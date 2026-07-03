"""BPE connector — land INSEE local-amenities counts into S3 Bronze.

Source: INSEE Melodi API (public, no authentication needed).
    Endpoint: https://api.insee.fr/melodi/data/DS_BPE

DS_BPE = Base Permanente des Équipements: per commune (GEO="YYYY-COM-xxxxx"),
the count (OBS_VALUE_NIVEAU) of facilities per type (FACILITY_TYPE) within a
domain (FACILITY_DOM A..G). Latest vintage = 2024. Carries the INSEE commune
code -> joins HOMEPEDIA. Like the population connector, it resolves the commune
list per department via geo.api.gouv.fr (+ arrondissements for Paris/Lyon/
Marseille), batches the Melodi requests and throttles them.

CLI:
    python -m src.data_ingestion.sources.bpe_connector --departement 69
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

DATASET = "bpe"
MELODI_URL = "https://api.insee.fr/melodi/data/DS_BPE"
GEO_API_URL = "https://geo.api.gouv.fr"
BATCH_SIZE = 20  # BPE is heavier per commune than population -> smaller batches
THROTTLE_DELAY = 3.0
LATEST_VINTAGE = 2024


class BPEConnector:
    """Ingest INSEE BPE amenity counts for a department into S3 Bronze."""

    def __init__(self, loader: S3Loader | None = None, bucket: str | None = None) -> None:
        self.loader = loader or S3Loader.from_env()
        self.bucket = bucket or os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")
        self.api_key = os.getenv("INSEE_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip('"').strip("'")

    @staticmethod
    def _bronze_key(year: int, departement: str) -> str:
        return bronze_key(DATASET, "bpe.json", year=year, departement=departement)

    @retry(max_attempts=4, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_communes(self, departement: str) -> list[dict]:
        url = (
            f"{GEO_API_URL}/departements/{departement}/communes"
            "?fields=code,nom,codeDepartement,codeRegion"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    @retry(max_attempts=4, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_melodi_batch(
        self, codes: list[str], year: int, geo_prefix: str = "COM"
    ) -> list[dict]:
        params = [("TIME_PERIOD", str(year))]
        for code in codes:
            params.append(("GEO", f"{geo_prefix}-{code}"))
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-INSEE-Api-Key-Production"] = self.api_key
        try:
            resp = requests.get(MELODI_URL, params=params, headers=headers, timeout=60)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                sleep_time = int(retry_after) if (retry_after and retry_after.isdigit()) else 60
                log.warning("bpe.melodi.rate_limit", sleep_time=sleep_time)
                time.sleep(sleep_time)
                resp = requests.get(MELODI_URL, params=params, headers=headers, timeout=60)
                resp.raise_for_status()
            else:
                raise
        return resp.json().get("observations", [])

    def ingest(self, year: int = LATEST_VINTAGE, departement: str = "",
               overwrite: bool = False) -> dict:
        key = self._bronze_key(year, departement)
        if not overwrite and self.loader.object_exists(self.bucket, key):
            log.info("bpe.skip.exists", key=key)
            return {"skipped": True, "key": key}

        self.loader.ensure_bucket(self.bucket)
        communes = self._fetch_communes(departement)
        arrondissements = fetch_arrondissements(departement)
        communes = communes + arrondissements
        commune_codes = [c["code"] for c in communes if "code" in c]
        if not commune_codes:
            return {"skipped": True, "reason": "no_communes_found"}

        arr_codes = {a["code"] for a in arrondissements}
        all_obs: list[dict] = []

        def _run(codes: list[str], geo_prefix: str) -> None:
            batches = [codes[i:i + BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)]
            for idx, batch in enumerate(batches):
                if all_obs or idx > 0:
                    time.sleep(THROTTLE_DELAY)
                all_obs.extend(self._fetch_melodi_batch(batch, year, geo_prefix))

        _run([c for c in commune_codes if c not in arr_codes], "COM")
        if arr_codes:
            _run(sorted(arr_codes), "ARM")

        fd, tmp = tempfile.mkstemp(prefix="bpe_", suffix=".json")
        os.close(fd)
        payload = {
            "dataset": DATASET, "year": year, "departement": departement,
            "communes": communes, "observations": all_obs,
        }
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        size = os.path.getsize(tmp)
        sha = hashlib.sha256()
        with open(tmp, "rb") as fh:
            while chunk := fh.read(1 << 20):
                sha.update(chunk)
        manifest = {
            "dataset": DATASET, "year": year, "departement": departement,
            "source_url": MELODI_URL, "bronze_uri": f"s3://{self.bucket}/{key}",
            "observations": len(all_obs), "bytes": size, "sha256": sha.hexdigest(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.loader.upload_file(
                bucket=self.bucket, key=key, local_path=tmp,
                content_type="application/json",
                metadata={"sha256": manifest["sha256"], "source_url": MELODI_URL},
            )
            manifest_key = key.rsplit("/", 1)[0] + "/_manifest.json"
            self.loader.put_json(self.bucket, manifest_key, manifest)
        finally:
            os.unlink(tmp)
        log.info("bpe.ingest.done", departement=departement, observations=len(all_obs))
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest INSEE BPE amenities into Bronze S3.")
    parser.add_argument("--year", type=int, default=LATEST_VINTAGE)
    parser.add_argument("--departement", type=str, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()
    manifest = BPEConnector().ingest(
        year=args.year, departement=args.departement, overwrite=args.overwrite
    )
    log.info("bpe.cli.result", **{k: manifest.get(k) for k in ("departement", "observations")})


if __name__ == "__main__":
    main()
