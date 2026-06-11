"""
Data-quality gate for the DVF Silver layer (runnable Spark job).

Loads rules from YAML, evaluates them on the Silver dataset via QualityMonitor,
logs a readable table, persists a JSON report to S3, and exits non-zero if any
*critical* check fails (so Airflow marks the task failed).

Run (inside the spark-master container):
    spark-submit src/data_governance/quality/data_quality_reporter.py --dataset dvf
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import yaml

from src.data_governance.quality.quality_monitor import CheckResult, QualityMonitor
from src.data_ingestion.loaders.s3_loader import S3Loader
from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark


def load_rules(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class QualityReporter:
    """Format, log and persist a quality report."""

    def __init__(self, loader: S3Loader | None = None, bucket: str | None = None) -> None:
        self.loader = loader or S3Loader.from_env()
        self.bucket = bucket or os.getenv("S3_SILVER_BUCKET", "homepedia-silver")

    def build_report(self, dataset: str, total: int, results: list[CheckResult]) -> dict:
        critical = [r for r in results if not r.passed and r.severity == "critical"]
        warnings = [r for r in results if not r.passed and r.severity == "warning"]
        return {
            "dataset": dataset,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "total_rows": total,
            "passed": len(critical) == 0,
            "critical_failures": len(critical),
            "warnings": len(warnings),
            "checks": [r.as_dict() for r in results],
        }

    @staticmethod
    def log_table(results: list[CheckResult]) -> None:
        for r in results:
            status = "PASS" if r.passed else ("FAIL" if r.severity == "critical" else "WARN")
            print(
                f"[quality] {status:4s} {r.name:22s} "
                f"obs={r.observed} thr={r.threshold}  ({r.detail})"
            )

    def persist(self, dataset: str, report: dict) -> str:
        ts = report["checked_at"].replace(":", "-")
        key = f"_quality/{dataset}/run={ts}.json"
        return self.loader.put_json(self.bucket, key, report)


def main() -> None:
    parser = argparse.ArgumentParser(description="DVF Silver data-quality gate")
    parser.add_argument("--dataset", default="dvf")
    parser.add_argument(
        "--rules", default="/opt/homepedia/config/data_quality/rules.yaml"
    )
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()

    spec = load_rules(args.rules)
    spark = build_spark("homepedia-quality-dvf")
    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(build_s3a_uri(args.silver_bucket, args.dataset))
    total, results = QualityMonitor(spec["rules"]).evaluate(df)

    reporter = QualityReporter()
    report = reporter.build_report(spec.get("dataset", args.dataset), total, results)
    reporter.log_table(results)
    uri = reporter.persist(args.dataset, report)

    print(
        f"[quality] dataset={report['dataset']} rows={total} "
        f"passed={report['passed']} critical_failures={report['critical_failures']} "
        f"warnings={report['warnings']} report={uri}"
    )
    spark.stop()
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
