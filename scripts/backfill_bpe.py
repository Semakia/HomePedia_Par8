"""One-off backfill: land INSEE BPE Bronze for all departements (vintage 2024).

Idempotent (skips objects already present). Runs from the host against real AWS
S3 via .env; throttled by the connector to respect the Melodi rate limit.

    python scripts/backfill_bpe.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DEPTS_FILE = ROOT / "airflow" / "dags" / "utils" / "departements.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    load_dotenv(ROOT / ".env")
    from src.data_ingestion.sources.bpe_connector import BPEConnector
    from src.data_ingestion.utils.logging_utils import configure_logging

    configure_logging()
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    deps = [str(d) for d in json.loads(DEPTS_FILE.read_text())["departements"]]

    connector = BPEConnector()
    landed = skipped = failed = 0
    for dep in deps:
        try:
            res = connector.ingest(year=year, departement=dep)
            if res.get("skipped"):
                skipped += 1
            else:
                landed += 1
        except Exception as exc:  # keep going on a single failure
            failed += 1
            print(f"FAIL {dep}: {exc}", flush=True)
        print(
            f"[{dep}] cumulative landed={landed} skipped={skipped} failed={failed}",
            flush=True,
        )
    print(f"ALL DONE landed={landed} skipped={skipped} failed={failed}", flush=True)


if __name__ == "__main__":
    main()
