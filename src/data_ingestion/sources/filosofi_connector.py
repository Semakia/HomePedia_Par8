"""FiLoSoFi connector — land raw INSEE localized income statistics into Bronze.

Source: INSEE Melodi API (public, no authentication needed).
    Endpoint: https://api.insee.fr/melodi/data/DS_FILOSOFI_CC

FiLoSoFi (Fichier Localisé Social et Fiscal) gives the localized standard of
living / disposable income per commune. The cube is keyed by GEO
("YYYY-COM-xxxxx"), TIME_PERIOD (latest vintage = 2023), UNIT_MEASURE and
FILOSOFI_MEASURE (MED_SL = median standard of living, D1_SL..D9_SL deciles,
GI_SL = Gini, PR_MD60 = poverty rate, ...). We land the raw observations; the
Silver job keeps MED_SL / EUR_YR (the median income) per commune.

Like the population connector, it resolves the commune list per department via
geo.api.gouv.fr, batches the Melodi requests, throttles to respect the rate
limit, and uploads the combined raw JSON to the Bronze layer of S3.

CLI:
    python -m src.data_ingestion.sources.filosofi_connector --year 2023 --departement 69
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone

import requests
from src.data_ingestion.loaders.s3_loader import S3Loader, bronze_key
from src.data_ingestion.utils.arrondissements import fetch_arrondissements
from src.data_ingestion.utils.logging_utils import configure_logging, get_logger
from src.data_ingestion.utils.retry_logic import retry

log = get_logger(__name__)

DATASET = "filosofi"
MELODI_URL = "https://api.insee.fr/melodi/data/DS_FILOSOFI_CC"
GEO_API_URL = "https://geo.api.gouv.fr"
BATCH_SIZE = 50
THROTTLE_DELAY = 3.0  # seconds between batches to respect the ~30 req/min limit
# FiLoSoFi is published with a lag; the latest commune vintage is 2023.
LATEST_VINTAGE = 2023


class FilosofiConnector:
    """Ingest INSEE FiLoSoFi income data for a department into S3 Bronze."""

    def __init__(self, loader: S3Loader | None = None, bucket: str | None = None) -> None:
        self.loader = loader or S3Loader.from_env()
        self.bucket = bucket or os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")
        self.api_key = os.getenv("INSEE_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip('"').strip("'")

    @staticmethod
    def _bronze_key(year: int, departement: str) -> str:
        return bronze_key(DATASET, "filosofi.json", year=year, departement=departement)

    @retry(
        max_attempts=4,
        base_delay=2.0,
        exceptions=(requests.RequestException,),
    )
    def _fetch_communes(self, departement: str) -> list[dict]:
        """List all communes of a department (code + metadata) via geo.api.gouv.fr."""
        url = (
            f"{GEO_API_URL}/departements/{departement}/communes"
            "?fields=code,nom,codeDepartement,codeRegion"
        )
        log.info("filosofi.geo_api.start", departement=departement, url=url)
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        log.info("filosofi.geo_api.done", departement=departement, count=len(data))
        return data

    @retry(
        max_attempts=4,
        base_delay=2.0,
        exceptions=(requests.RequestException,),
    )
    def _fetch_melodi_batch(
        self, codes: list[str], year: int, geo_prefix: str = "COM"
    ) -> list[dict]:
        """Query the FiLoSoFi cube for a batch of GEO codes.

        geo_prefix is "COM" for communes, "ARM" for municipal arrondissements.
        """
        params = [("TIME_PERIOD", str(year))]
        for code in codes:
            params.append(("GEO", f"{geo_prefix}-{code}"))

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-INSEE-Api-Key-Production"] = self.api_key

        log.info(
            "filosofi.melodi.batch.start",
            count=len(codes),
            authenticated=bool(self.api_key),
        )
        try:
            resp = requests.get(MELODI_URL, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                sleep_time = int(retry_after) if (retry_after and retry_after.isdigit()) else 60
                log.warning("filosofi.melodi.rate_limit", error=str(e), sleep_time=sleep_time)
                time.sleep(sleep_time)
                resp = requests.get(MELODI_URL, params=params, headers=headers, timeout=30)
                resp.raise_for_status()
            else:
                raise

        data = resp.json()
        observations = data.get("observations", [])
        log.info("filosofi.melodi.batch.done", count=len(codes), observations=len(observations))
        return observations

    def ingest(self, year: int, departement: str, overwrite: bool = False) -> dict:
        """Ingest FiLoSoFi income data for a department and land it in Bronze S3."""
        key = self._bronze_key(year, departement)
        if not overwrite and self.loader.object_exists(self.bucket, key):
            log.info("filosofi.skip.exists", bucket=self.bucket, key=key)
            return {"skipped": True, "bucket": self.bucket, "key": key}

        self.loader.ensure_bucket(self.bucket)

        try:
            communes = self._fetch_communes(departement)
            arrondissements = fetch_arrondissements(departement)
        except Exception as e:
            log.error("filosofi.geo_api.failed", departement=departement, error=str(e))
            raise
        # Arrondissements join the referential so Silver can resolve their names.
        communes = communes + arrondissements

        commune_codes = [c["code"] for c in communes if "code" in c]
        if not commune_codes:
            log.warning("filosofi.ingest.no_communes", departement=departement)
            return {"skipped": True, "reason": "no_communes_found"}

        # Communes queried as COM-, arrondissements as ARM-.
        arr_codes = {a["code"] for a in arrondissements}
        all_observations: list[dict] = []

        def _run_batches(codes: list[str], geo_prefix: str) -> None:
            batches = [
                codes[i:i + BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)
            ]
            for idx, batch in enumerate(batches):
                if all_observations or idx > 0:
                    log.info("filosofi.throttle.wait", delay=THROTTLE_DELAY)
                    time.sleep(THROTTLE_DELAY)
                try:
                    all_observations.extend(
                        self._fetch_melodi_batch(batch, year, geo_prefix=geo_prefix)
                    )
                except Exception as e:
                    log.error("filosofi.melodi.batch.failed", error=str(e))
                    raise

        _run_batches([c for c in commune_codes if c not in arr_codes], "COM")
        if arr_codes:
            _run_batches(sorted(arr_codes), "ARM")

        log.info("filosofi.save.temp", total_observations=len(all_observations))
        fd, tmp_path = tempfile.mkstemp(prefix="filosofi_", suffix=".json")
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
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

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

        log.info("filosofi.ingest.done", **{k: manifest[k] for k in ("bronze_uri", "bytes")})
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest INSEE FiLoSoFi income data into Bronze S3.")
    parser.add_argument("--year", type=int, default=LATEST_VINTAGE, help="Vintage year (latest = 2023)")
    parser.add_argument("--departement", type=str, required=True, help="2- or 3-char dept code")
    parser.add_argument("--overwrite", action="store_true", help="Re-land even if present")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()
    manifest = FilosofiConnector().ingest(
        year=args.year, departement=args.departement, overwrite=args.overwrite
    )
    log.info("filosofi.cli.result", **manifest)


if __name__ == "__main__":
    main()
