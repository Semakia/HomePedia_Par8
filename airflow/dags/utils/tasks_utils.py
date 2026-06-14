"""Task callables for the homepedia_etl DAG, grouped in a class.

homepedia_etl.py instantiates HomepediaETLTasks and passes its bound methods as
PythonOperator callables, so the DAG module stays purely declarative.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.data_ingestion.sources.dvf_connector import DVFConnector
from src.data_ingestion.utils.logging_utils import configure_logging, get_logger


class HomepediaETLTasks:
    """Callables backing the homepedia_etl DAG tasks."""

    def __init__(self, departements_file: Path | None = None) -> None:
        # Canonical DVF departement list lives next to this module by default.
        self.departements_file = departements_file or (
            Path(__file__).parent / "departements.json"
        )
        configure_logging()
        self.logger = get_logger()

    # helpers
    def load_departements(self) -> list[str]:
        """Return the canonical DVF departement codes from the JSON sidecar."""
        with open(self.departements_file, encoding="utf-8") as fh:
            return [str(d) for d in json.load(fh)["departements"]]

    # ingestion
    def ingest_dvf(self, **context) -> dict:
        """Land DVF files into Bronze S3 for the requested year/departements.

        Idempotent (the connector skips existing objects). Default (no subset in
        the run config) = every departement in the JSON. Returns an XCom summary.
        """
        params = context["params"]
        year = int(params["year"])
        # Optional subset via the run config; default = every departement listed.
        requested = [str(d) for d in (params.get("departements") or [])]
        departements = requested or self.load_departements()

        connector = DVFConnector()
        results: list[dict] = []
        for dep in departements:
            results.append(connector.ingest(year=year, departement=dep))

        landed = [r for r in results if not r.get("skipped")]
        self.logger.info(
            "dvf.ingest.summary",
            year=year,
            requested=len(results),
            landed=len(landed),
            skipped=len(results) - len(landed),
        )
        return {"year": year, "objects": results}

    def ingest_insee(self, **context) -> dict:
        """Land INSEE population files into Bronze S3 for the requested year/departements.

        Idempotent: the connector skips objects already present (no overwrite).
        Returns a summary pushed to XCom.
        """
        params = context["params"]
        requested_year = int(params["year"])
        # INSEE Melodi RP cube only serves 2011/2016/2022; 2022 is the latest
        # population vintage. Cap the request so a recent DVF year (e.g. 2024)
        # still lands the most recent INSEE data available.
        year = min(requested_year, 2022)
        requested = [str(d) for d in (params.get("departements") or [])]
        departements = requested or self.load_departements()

        from src.data_ingestion.sources.insee_connector import InseeConnector

        connector = InseeConnector()
        results: list[dict] = []

        for dep in departements:
            results.append(connector.ingest(year=year, departement=dep))

        landed = [r for r in results if not r.get("skipped")]
        self.logger.info(
            "insee.ingest.summary",
            year=year,
            requested=len(results),
            landed=len(landed),
            skipped=len(results) - len(landed),
        )
        return {"year": year, "objects": results}

    def ingest_filosofi(self, **context) -> dict:
        """Land INSEE FiLoSoFi income files into Bronze S3 for each departement.

        Idempotent: the connector skips objects already present (no overwrite).
        Returns a summary pushed to XCom.
        """
        params = context["params"]
        requested_year = int(params["year"])
        # FiLoSoFi commune vintage caps at 2023 (published with a lag). Cap the
        # request so a recent DVF year still lands the latest income data.
        year = min(requested_year, 2023)
        requested = [str(d) for d in (params.get("departements") or [])]
        departements = requested or self.load_departements()

        from src.data_ingestion.sources.filosofi_connector import FilosofiConnector

        connector = FilosofiConnector()
        results: list[dict] = []
        for dep in departements:
            results.append(connector.ingest(year=year, departement=dep))

        landed = [r for r in results if not r.get("skipped")]
        self.logger.info(
            "filosofi.ingest.summary",
            year=year,
            requested=len(results),
            landed=len(landed),
            skipped=len(results) - len(landed),
        )
        return {"year": year, "objects": results}

    # downstream (stubs)
    # NB: silver_to_gold is NOT here — it runs as a Spark JDBC job inside the
    # spark-master container (BashOperator docker exec in the DAG), since it
    # needs the Spark runtime + Postgres driver baked into the spark image.
    def refresh_cache(self, **_) -> None:
        self.logger.info("[cache] would warm Redis pre-computed views. Stub for now.")
