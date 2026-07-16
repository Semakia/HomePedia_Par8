"""Publish HOMEPEDIA data-quality results to OpenMetadata.

Host-run bridge, decoupled from Spark: reads the latest quality report that
`data_quality_reporter` wrote to S3 (`_quality/<dataset>/run=*.json`) and pushes
it to OpenMetadata as Data Quality test results on the matching catalog table.

Two flavours of target table (see DATASETS):
  - DVF Silver is NOT cataloged elsewhere -> we create a small logical table
    (ensure_catalog) and attach the tests to it.
  - Gold tables are already cataloged by OM's Postgres connector -> we attach
    the tests to their existing FQN (no catalog creation).

Why a host bridge and the S3 JSON as the contract:
  - the reporter runs in the Spark container (homepedia-net); OM is on app_net,
    so a direct push would need cross-network plumbing;
  - the S3 report already holds every CheckResult — a clean integration seam.
We authenticate with the OM *admin* login token (full perms), sidestepping the
ingestion-bot token rotation pitfalls.

Run (from repo root, with .env present):
    python -m src.data_governance.metadata.openmetadata_sync --dataset dvf
    python -m src.data_governance.metadata.openmetadata_sync --dataset gold_city_metrics
    python -m src.data_governance.metadata.openmetadata_sync --dataset gold_demographics
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime

import boto3
from dotenv import load_dotenv

# --- DVF Silver logical table (created here; not cataloged elsewhere) ---------
DVF_SERVICE = "homepedia"
DVF_DATABASE = "silver"
DVF_SCHEMA = "dvf"
DVF_TABLE = "dvf_silver"
DVF_FQN = f"{DVF_SERVICE}.{DVF_DATABASE}.{DVF_SCHEMA}.{DVF_TABLE}"
DVF_COLUMNS = [
    ("id_mutation", "STRING"), ("date_mutation", "DATE"), ("year", "INT"),
    ("month", "INT"), ("code_commune", "STRING"), ("code_departement", "STRING"),
    ("nom_commune", "STRING"), ("type_local", "STRING"),
    ("surface_reelle_bati", "DOUBLE"), ("nombre_pieces_principales", "INT"),
    ("valeur_fonciere", "DOUBLE"), ("prix_m2", "DOUBLE"),
    ("longitude", "DOUBLE"), ("latitude", "DOUBLE"),
]

TEST_DEFINITION = "homepediaQualityCheck"

# dataset (S3 _quality/<dataset>/) -> OM table FQN. Gold tables are already
# cataloged by the Postgres connector (logical=False -> tests only).
DATASETS = {
    "dvf": {"fqn": DVF_FQN, "logical": True},
    "gold_city_metrics": {
        "fqn": "homepedia_gold.homepedia_gold_dev.market.city_metrics",
        "logical": False,
    },
    "gold_demographics": {
        "fqn": "homepedia_gold.homepedia_gold_dev.demographics.commune_profile",
        "logical": False,
    },
    "gold_mobility": {
        "fqn": "homepedia_gold.homepedia_gold_dev.mobility.commune_transport",
        "logical": False,
    },
    "gold_services": {
        "fqn": "homepedia_gold.homepedia_gold_dev.services.commune_equipements",
        "logical": False,
    },
}


class OpenMetadataClient:
    def __init__(self, table_fqn: str, host: str | None = None) -> None:
        self.base = (host or os.getenv("OM_HOST", "http://localhost:8585")) + "/api/v1"
        self.table_fqn = table_fqn
        self.entity_link = f"<#E::table::{table_fqn}>"
        self.token = self._login()

    def _req(self, path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method)
        r.add_header("Content-Type", "application/json")
        if getattr(self, "token", None):
            r.add_header("Authorization", "Bearer " + self.token)
        try:
            resp = urllib.request.urlopen(r, timeout=90)
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read())
            except Exception:  # noqa: BLE001
                return exc.code, {}

    def _login(self) -> str:
        pw = base64.b64encode(
            os.getenv("OM_ADMIN_PASSWORD", "admin").encode()
        ).decode()
        email = os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org")
        _, body = self._req(
            "/users/login", "POST", {"email": email, "password": pw}
        )
        return body["accessToken"]

    # --- DVF logical catalog (idempotent via PUT createOrUpdate) ----------
    def ensure_dvf_catalog(self) -> None:
        self._req("/services/databaseServices", "PUT", {
            "name": DVF_SERVICE, "serviceType": "CustomDatabase",
            "connection": {"config": {
                "type": "CustomDatabase",
                "sourcePythonClass":
                    "metadata.ingestion.source.database.customdatabase."
                    "customdatabaseconnection.CustomDatabaseSource",
            }},
        })
        self._req("/databases", "PUT", {"name": DVF_DATABASE, "service": DVF_SERVICE})
        self._req("/databaseSchemas", "PUT",
                  {"name": DVF_SCHEMA, "database": f"{DVF_SERVICE}.{DVF_DATABASE}"})
        self._req("/tables", "PUT", {
            "name": DVF_TABLE,
            "databaseSchema": f"{DVF_SERVICE}.{DVF_DATABASE}.{DVF_SCHEMA}",
            "description": "DVF Silver — cleaned French housing transactions.",
            "columns": [{"name": n, "dataType": t} for n, t in DVF_COLUMNS],
        })

    # --- data quality scaffolding -----------------------------------------
    # The table's executable test suite is auto-created by OM when the first
    # test case is added via its entityLink — no explicit suite call.
    def ensure_test_definition(self) -> None:
        self._req("/dataQuality/testDefinitions", "PUT", {
            "name": TEST_DEFINITION,
            "displayName": "HOMEPEDIA quality check",
            "description": "Generic pass/fail rule from the HOMEPEDIA quality engine.",
            "entityType": "TABLE",
            "testPlatforms": ["OpenMetadata"],
            "parameterDefinition": [{"name": "threshold"}],
        })

    def ensure_test_case(self, name: str) -> str:
        code, body = self._req("/dataQuality/testCases", "POST", {
            "name": name,
            "entityLink": self.entity_link,
            "testDefinition": TEST_DEFINITION,
            "parameterValues": [],
        })
        if code < 400 and body.get("fullyQualifiedName"):
            return body["fullyQualifiedName"]
        # Already exists -> fetch its FQN.
        _, got = self._req(
            f"/dataQuality/testCases/name/{self.table_fqn}.{name}?fields=", "GET"
        )
        return got.get("fullyQualifiedName", f"{self.table_fqn}.{name}")

    def push_result(self, test_case_fqn: str, check: dict, when_ms: int) -> int:
        status = "Success" if check["passed"] else "Failed"
        code, _ = self._req(
            f"/dataQuality/testCases/testCaseResults/{test_case_fqn}", "POST", {
                "timestamp": when_ms,
                "testCaseStatus": status,
                "result": (
                    f"[{check['severity']}] observed={check['observed']} "
                    f"threshold={check['threshold']} — {check['detail']}"
                ),
                "testResultValue": [
                    {"name": "observed", "value": str(check["observed"])},
                    {"name": "threshold", "value": str(check["threshold"])},
                ],
            })
        return code


def latest_report(dataset: str) -> dict:
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "eu-north-1"))
    bucket = os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"_quality/{dataset}/")
    keys = sorted(o["Key"] for o in resp.get("Contents", []))
    if not keys:
        raise SystemExit(f"No quality report under _quality/{dataset}/ in {bucket}")
    obj = s3.get_object(Bucket=bucket, Key=keys[-1])
    return json.loads(obj["Body"].read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync quality report -> OpenMetadata")
    parser.add_argument("--dataset", default="dvf", choices=sorted(DATASETS))
    args = parser.parse_args()
    load_dotenv()

    cfg = DATASETS[args.dataset]
    report = latest_report(args.dataset)
    when_ms = int(datetime.now(UTC).timestamp() * 1000)

    om = OpenMetadataClient(cfg["fqn"])
    if cfg["logical"]:
        om.ensure_dvf_catalog()
    om.ensure_test_definition()

    ok = 0
    for check in report["checks"]:
        fqn = om.ensure_test_case(check["name"])
        code = om.push_result(fqn, check, when_ms)
        state = "OK" if code < 400 else f"ERR {code}"
        ok += code < 400
        print(f"  {check['name']:24s} {('PASS' if check['passed'] else 'FAIL'):4s} -> {state}")

    print(
        f"\n[om-sync] table={cfg['fqn']} rows={report['total_rows']} "
        f"pushed {ok}/{len(report['checks'])} checks (report passed={report['passed']})"
    )


if __name__ == "__main__":
    main()
