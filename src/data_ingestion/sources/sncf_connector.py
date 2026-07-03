"""SNCF connector — land train-station open data into Bronze.

Source: SNCF open data (Opendatasoft, public, no auth).
    https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/<ds>/exports/json

Two datasets land the mobility layer:
  - gares-de-voyageurs : passenger-station referential (nom, codeinsee, UIC,
    segment_drg, geo). Carries the INSEE commune code -> joins HOMEPEDIA.
  - frequentation-gares : annual passenger counts per station (UIC).

The connector only *lands* the raw JSON (Bronze = untouched); the join and the
per-commune aggregation happen in Silver/Gold.

CLI:
    python -m src.data_ingestion.sources.sncf_connector
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone

import requests
from src.data_ingestion.loaders.s3_loader import S3Loader
from src.data_ingestion.utils.logging_utils import configure_logging, get_logger
from src.data_ingestion.utils.retry_logic import retry

log = get_logger(__name__)

DATASET = "sncf"
ODS_BASE = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets"

# (dataset id, selected fields) for each SNCF export, keyed by bronze filename.
EXPORTS = {
    "gares": (
        "gares-de-voyageurs",
        "nom,codes_uic,codeinsee,segment_drg,position_geographique",
    ),
    "frequentation": (
        "frequentation-gares",
        "nom_gare,code_uic_complet,segmentation_drg,"
        "total_voyageurs_2024,total_voyageurs_2023,total_voyageurs_2022",
    ),
}


class SNCFConnector:
    """Land SNCF station open data in the Bronze bucket."""

    def __init__(self, loader: S3Loader | None = None, bucket: str | None = None) -> None:
        self.loader = loader or S3Loader.from_env()
        self.bucket = bucket or os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")

    @retry(max_attempts=4, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_export(
        self,
        ods_dataset: str,
        select: str
    ) -> list[dict]:
        """Fetch a SNCF export from Opendatasoft.
        Args:
            ods_dataset : SNCF Opendatasoft dataset id (e.g. "gares-de-voyageurs")
            select : comma-separated list of fields to select from the ODS
        Returns: list of records (dicts)
        """
        url = f"{ODS_BASE}/{ods_dataset}/exports/json"
        params = {"limit": -1, "select": select}
        log.info("sncf.export.start", dataset=ods_dataset)
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        log.info("sncf.export.done", dataset=ods_dataset, records=len(data))
        return data

    def _land(
        self,
        name: str,
        ods_dataset: str,
        select: str,
        overwrite: bool
    ) -> dict:
        """
        Land a single SNCF export into Bronze S3.
        Args:
            name : bronze filename (e.g. "gares")
            ods_dataset : SNCF Opendatasoft dataset id (e.g. "gares-de-voyageurs")
            select : comma-separated list of fields to select from the ODS
            overwrite : if True, re-land even if the file already exists in S3
        """
        key = f"{DATASET}/{name}.json"
        if not overwrite and self.loader.object_exists(self.bucket, key):
            log.info("sncf.skip.exists", key=key)
            return {"skipped": True, "key": key}

        records = self._fetch_export(ods_dataset, select)
        payload = {"dataset": ods_dataset, "records": records}

        fd, tmp = tempfile.mkstemp(prefix=f"sncf_{name}_", suffix=".json")
        os.close(fd)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        size = os.path.getsize(tmp)
        sha = hashlib.sha256()
        with open(tmp, "rb") as fh:
            while chunk := fh.read(1 << 20):
                sha.update(chunk)

        manifest = {
            "dataset": DATASET,
            "source": ods_dataset,
            "bronze_uri": f"s3://{self.bucket}/{key}",
            "records": len(records),
            "bytes": size,
            "sha256": sha.hexdigest(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.loader.upload_file(
                bucket=self.bucket, key=key, local_path=tmp,
                content_type="application/json",
                metadata={"sha256": manifest["sha256"], "source": ods_dataset},
            )
            self.loader.put_json(
                self.bucket, f"{DATASET}/_manifest_{name}.json", manifest
            )
        finally:
            os.unlink(tmp)
        log.info("sncf.land.done", **{k: manifest[k] for k in ("bronze_uri", "records")})
        return manifest

    def ingest(self, overwrite: bool = False) -> dict:
        self.loader.ensure_bucket(self.bucket)
        results = {
            name: self._land(name, ods, select, overwrite)
            for name, (ods, select) in EXPORTS.items()
        }
        return {"dataset": DATASET, "exports": results}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ingest SNCF station data into Bronze S3.")
    parser.add_argument("--overwrite", action="store_true", help="Re-land even if present")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()
    result = SNCFConnector().ingest(overwrite=args.overwrite)
    log.info(
        "sncf.cli.result",
        **{k: v.get("records") for k, v in result["exports"].items()},
    )


if __name__ == "__main__":
    main()
