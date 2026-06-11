"""DVF connector — land raw 'Demandes de Valeurs Foncières' files into Bronze.

Source: geo-dvf (Etalab open data), gzipped CSV, no API key.
    https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/full.csv.gz
    https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dd}.csv.gz

This is the housing-prices source at the heart of HOMEPEDIA. The connector only
*lands* bytes (Bronze = raw, untouched); cleaning/typing happens later in the
Silver Spark job. Each run writes the data object + a `_manifest.json` provenance
sidecar so Silver and the data catalog can trust what arrived.

CLI:
    python -m src.data_ingestion.sources.dvf_connector --year 2024
    python -m src.data_ingestion.sources.dvf_connector --year 2024 --departement 75
"""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from src.data_ingestion.loaders.s3_loader import S3Loader, bronze_key
from src.data_ingestion.utils.logging_utils import configure_logging, get_logger
from src.data_ingestion.utils.retry_logic import retry

log = get_logger(__name__)

DATASET = "dvf"
BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv"
CHUNK_SIZE = 1 << 20  # 1 MiB


@dataclass
class FetchResult:
    local_path: str
    bytes: int
    sha256: str
    source_url: str
    content_type: str


class DVFConnector:
    """
        Fetch DVF gz CSVs and land them in the Bronze bucket.
    """

    def __init__(self, loader: S3Loader | None = None, bucket: str | None = None) -> None:
        self.loader = loader or S3Loader.from_env()
        self.bucket = bucket or os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")

    # --- url / key resolution ---------------------------------------------
    @staticmethod
    def _source_url(year: int, departement: str | None) -> str:
        if departement:
            return f"{BASE_URL}/{year}/departements/{departement}.csv.gz"
        return f"{BASE_URL}/{year}/full.csv.gz"

    @staticmethod
    def _bronze_key(year: int, departement: str | None) -> str:
        if departement:
            return bronze_key(
                DATASET, f"{departement}.csv.gz", year=year, departement=departement
            )
        return bronze_key(DATASET, "full.csv.gz", year=year)

    # --- fetch -------------------------------------------------------------
    @retry(
        max_attempts=4,
        base_delay=2.0,
        exceptions=(requests.RequestException,),
    )
    def _download(self, url: str) -> FetchResult:
        """
            Stream the remote file to a temp path, hashing as we go.
            Args: the source URL to fetch
            Returns: a FetchResult with the local path, byte size, sha256,
            and content
        """
        log.info("dvf.download.start", url=url)
        sha = hashlib.sha256()
        total = 0
        fd, tmp_path = tempfile.mkstemp(prefix="dvf_", suffix=".csv.gz")
        os.close(fd)
        with requests.get(url, stream=True, timeout=(10, 300)) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "application/gzip")
            with open(tmp_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    sha.update(chunk)
                    total += len(chunk)
        log.info("dvf.download.done", url=url, bytes=total)
        return FetchResult(tmp_path, total, sha.hexdigest(), url, content_type)

    # --- orchestration -----------------------------------------------------
    def ingest(
        self, year: int, departement: str | None = None, overwrite: bool = False
    ) -> dict:
        """
            Download one DVF file and land it (+ manifest) in Bronze.

            Returns the manifest dict. Idempotent: skips if the object already
            exists unless `overwrite=True`.
        """
        key = self._bronze_key(year, departement)
        if not overwrite and self.loader.object_exists(self.bucket, key):
            log.info("dvf.skip.exists", bucket=self.bucket, key=key)
            return {"skipped": True, "bucket": self.bucket, "key": key}

        self.loader.ensure_bucket(self.bucket)
        url = self._source_url(year, departement)
        result = self._download(url)

        manifest = {
            "dataset": DATASET,
            "year": year,
            "departement": departement,
            "source_url": result.source_url,
            "bronze_uri": f"s3://{self.bucket}/{key}",
            "bytes": result.bytes,
            "sha256": result.sha256,
            "content_type": result.content_type,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.loader.upload_file(
                bucket=self.bucket,
                key=key,
                local_path=result.local_path,
                content_type=result.content_type,
                metadata={"sha256": result.sha256, "source_url": result.source_url},
            )
            manifest_key = key.rsplit("/", 1)[0] + "/_manifest.json"
            self.loader.put_json(self.bucket, manifest_key, manifest)
        finally:
            os.unlink(result.local_path)

        log.info("dvf.ingest.done", **{k: manifest[k] for k in ("bronze_uri", "bytes")})
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest DVF data into Bronze S3.")
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Vintage year, e.g. 2024"
    )
    parser.add_argument(
        "--departement",
        type=str,
        default=None,
        help="2- or 3-char dept code (e.g. 75, 2A, 971). Omit for the full-year file.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Re-land even if present")
    args = parser.parse_args()

    # Load .env so a single config file drives the target (MinIO or AWS S3).
    # No-op inside containers where config comes from the environment directly.
    from dotenv import load_dotenv

    load_dotenv()

    configure_logging()
    manifest = DVFConnector().ingest(
        year=args.year, departement=args.departement, overwrite=args.overwrite
    )
    log.info("dvf.cli.result", **manifest)


if __name__ == "__main__":
    main()
