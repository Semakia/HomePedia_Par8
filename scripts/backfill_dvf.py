"""One-off backfill: land DVF Bronze for several years x all departements.

Idempotent (the connector skips objects already present). Runs from the host
against real AWS S3 via .env. Decoupled from the Airflow container (which can
restart and kill a docker exec mid-run).

    python scripts/backfill_dvf.py            # default years 2021..2025
    python scripts/backfill_dvf.py 2023 2024  # explicit subset
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DEPTS_FILE = ROOT / "airflow" / "dags" / "utils" / "departements.json"

# Allow `python scripts/backfill_dvf.py` from anywhere: put repo root on path.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    load_dotenv(ROOT / ".env")
    from src.data_ingestion.sources.dvf_connector import DVFConnector
    from src.data_ingestion.utils.logging_utils import configure_logging

    configure_logging()

    default_years = [2021, 2022, 2023, 2024, 2025]
    years = [int(a) for a in sys.argv[1:]] or default_years
    deps = [str(d) for d in json.loads(DEPTS_FILE.read_text())["departements"]]

    connector = DVFConnector()
    landed = skipped = failed = 0
    for year in years:
        for dep in deps:
            try:
                res = connector.ingest(year=year, departement=dep)
                if res.get("skipped"):
                    skipped += 1
                else:
                    landed += 1
            except Exception as exc:  # keep going on a single failure
                failed += 1
                print(f"FAIL {year}/{dep}: {exc}", flush=True)
        print(
            f"[year {year}] done. cumulative "
            f"landed={landed} skipped={skipped} failed={failed}",
            flush=True,
        )
    print(f"ALL DONE landed={landed} skipped={skipped} failed={failed}", flush=True)


if __name__ == "__main__":
    main()
