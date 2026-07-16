"""INSEE population connector — land raw census population statistics into S3 Bronze.

Source: INSEE Melodi API (public, no authentication needed).
    Endpoint: https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC

This connector retrieves the population statistics for all communes of a given
department dynamically, using the official administrative API (geo.api.gouv.fr)
to resolve the list of communes. It batches the requests (by 50 communes) to
respect HTTP URL limits, throttles requests to avoid hitting rate limits (30 req/min),
and uploads the combined raw JSON to the Bronze layer of S3.

CLI:
    python -m src.data_ingestion.sources.insee_connector --year 2022 --departement 69
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from src.data_ingestion.loaders.s3_loader import S3Loader, bronze_key
from src.data_ingestion.utils.arrondissements import fetch_arrondissements
from src.data_ingestion.utils.logging_utils import configure_logging, get_logger
from src.data_ingestion.utils.retry_logic import retry

log = get_logger(__name__)

DATASET = "insee"
MELODI_URL = "https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC"
GEO_API_URL = "https://geo.api.gouv.fr"
BATCH_SIZE = 50
THROTTLE_DELAY = 3.0  # seconds between batch requests to respect 30 req/min rate limit


@dataclass
class FetchResult:
    local_path: str
    bytes: int
    content_type: str


class InseeConnector:
    """
    Ingest INSEE population data for a department into the S3 Bronze bucket.
    """

    def __init__(self, loader: S3Loader | None = None, bucket: str | None = None) -> None:
        self.loader = loader or S3Loader.from_env()
        self.bucket = bucket or os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")
        self.api_key = os.getenv("INSEE_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip('"').strip("'")

    @staticmethod
    def _bronze_key(year: int, departement: str) -> str:
        return bronze_key(DATASET, "population.json", year=year, departement=departement)

    @retry(
        max_attempts=4,
        base_delay=2.0,
        exceptions=(requests.RequestException,),
    )
    def _fetch_communes(self, departement: str) -> list[dict]:
        """
        Query geo.api.gouv.fr to list all communes in a given department with their metadata.
        """
        url = (
            f"{GEO_API_URL}/departements/{departement}/communes"
            "?fields=code,nom,codeDepartement,codeRegion"
        )
        log.info("insee.geo_api.start", departement=departement, url=url)
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        log.info("insee.geo_api.done", departement=departement, count=len(data))
        return data

    @retry(
        max_attempts=4,
        base_delay=2.0,
        exceptions=(requests.RequestException,),
    )
    def _fetch_melodi_batch(
        self,
        codes: list[str],
        year: int,
        geo_prefix: str = "COM"
    ) -> list[dict]:
        """
        Query INSEE Melodi API for a batch of GEO codes.

        geo_prefix is "COM" for communes, "ARM" for municipal arrondissements
        (Paris/Lyon/Marseille), which the cube keys under the ARM- GEO type.
        """
        params = [("TIME_PERIOD", str(year))]
        for code in codes:
            params.append(("GEO", f"{geo_prefix}-{code}"))

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-INSEE-Api-Key-Production"] = self.api_key

        log.info("insee.melodi.batch.start", count=len(codes), authenticated=bool(self.api_key))

        try:
            resp = requests.get(MELODI_URL, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                sleep_time = int(retry_after) if (retry_after and retry_after.isdigit()) else 60
                log.warning("insee.melodi.rate_limit", error=str(e), sleep_time=sleep_time)
                time.sleep(sleep_time)
                resp = requests.get(MELODI_URL, params=params, headers=headers, timeout=30)
                resp.raise_for_status()
            else:
                raise

        data = resp.json()
        observations = data.get("observations", [])
        log.info("insee.melodi.batch.done", count=len(codes), observations=len(observations))
        return observations

    def ingest(
        self,
        year: int,
        departement: str,
        overwrite: bool = False
    ) -> dict:
        """
        Ingest INSEE population data for a department and land it in Bronze S3.
        Args:
            year : vintage year (e.g. 2022)
            departement : 2- or 3-char department code (e.g. 75, 69, 13)
            overwrite : if True, re-land even if the file already exists in S3
        Returns: manifest dict with metadata about the landed file
        """
        key = self._bronze_key(year, departement)
        if not overwrite and self.loader.object_exists(self.bucket, key):
            log.info("insee.skip.exists", bucket=self.bucket, key=key)
            return {"skipped": True, "bucket": self.bucket, "key": key}

        self.loader.ensure_bucket(self.bucket)

        # 1. Fetch communes metadata from department (+ arrondissements for
        #    Paris/Lyon/Marseille, so their ARM- figures can be landed too).
        try:
            communes = self._fetch_communes(departement)
            arrondissements = fetch_arrondissements(departement)
        except Exception as e:
            log.error("insee.geo_api.failed", departement=departement, error=str(e))
            raise
        # Arrondissements join the referential so Silver can resolve their names.
        communes = communes + arrondissements

        commune_codes = [c["code"] for c in communes if "code" in c]

        if not commune_codes:
            log.warning("insee.ingest.no_communes", departement=departement)
            return {"skipped": True, "reason": "no_communes_found"}

        # 2. Fetch observations from Melodi in throttled batches. Communes are
        #    queried as COM-, arrondissements as ARM-.
        arr_codes = {a["code"] for a in arrondissements}
        all_observations = []

        def _run_batches(
            codes: list[str],
            geo_prefix: str
        ) -> None:
            batches = [
                codes[i:i + BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)
            ]
            for idx, batch in enumerate(batches):
                if all_observations or idx > 0:
                    log.info("insee.throttle.wait", delay=THROTTLE_DELAY)
                    time.sleep(THROTTLE_DELAY)
                try:
                    all_observations.extend(
                        self._fetch_melodi_batch(batch, year, geo_prefix=geo_prefix)
                    )
                except Exception as e:
                    log.error("insee.melodi.batch.failed", error=str(e))
                    raise

        _run_batches(
            [c for c in commune_codes if c not in arr_codes],
            "COM"
        )
        if arr_codes:
            _run_batches(sorted(arr_codes), "ARM")

        # 3. Format and serialize data to local temp file
        log.info("insee.save.temp", total_observations=len(all_observations))
        fd, tmp_path = tempfile.mkstemp(prefix="insee_population_", suffix=".json")
        os.close(fd)

        output_data = {
            "dataset": DATASET,
            "year": year,
            "departement": departement,
            "communes": communes,
            "observations": all_observations,
        }

        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(output_data, fh, ensure_ascii=False, indent=2)

        file_size = os.path.getsize(tmp_path)

        # Hash local file to get sha256
        sha = hashlib.sha256()
        with open(tmp_path, "rb") as fh:
            while chunk := fh.read(1 << 20):
                sha.update(chunk)
        sha256 = sha.hexdigest()

        content_type = "application/json"

        manifest = {
            "dataset": DATASET,
            "year": year,
            "departement": departement,
            "source_url": MELODI_URL,
            "bronze_uri": f"s3://{self.bucket}/{key}",
            "bytes": file_size,
            "sha256": sha256,
            "content_type": content_type,
            "ingested_at": datetime.now(UTC).isoformat(),
        }

        # 4. Upload to Bronze S3
        try:
            self.loader.upload_file(
                bucket=self.bucket,
                key=key,
                local_path=tmp_path,
                content_type=content_type,
                metadata={"sha256": sha256, "source_url": MELODI_URL},
            )
            manifest_key = key.rsplit("/", 1)[0] + "/_manifest.json"
            self.loader.put_json(self.bucket, manifest_key, manifest)
        finally:
            os.unlink(tmp_path)

        log.info("insee.ingest.done", **{k: manifest[k] for k in ("bronze_uri", "bytes")})
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest INSEE population data into Bronze S3.")
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Vintage year, e.g. 2022"
    )
    parser.add_argument(
        "--departement",
        type=str,
        required=True,
        help="2- or 3-char dept code (e.g. 75, 69, 13)."
    )
    parser.add_argument("--overwrite", action="store_true", help="Re-land even if present")
    args = parser.parse_args()

    # Load .env for local credentials
    from dotenv import load_dotenv

    load_dotenv()

    configure_logging()
    manifest = InseeConnector().ingest(
        year=args.year, departement=args.departement, overwrite=args.overwrite
    )
    log.info("insee.cli.result", **manifest)


if __name__ == "__main__":
    main()
