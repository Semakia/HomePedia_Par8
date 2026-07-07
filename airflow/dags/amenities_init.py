"""HOMEPEDIA - Services / amenities ETL DAG (INSEE BPE).

Pipeline: ingest_bpe -> bronze_to_silver_bpe -> services_to_gold -> quality

INSEE BPE (Base Permanente des Équipements) -> Bronze S3, cleaned to Silver
(one row per commune × facility type), pivoted to the Gold `services` schema
(services.commune_equipements: counts by domain + key amenities + level). Spark
jobs run on the on-demand GCP VM in prod (local container in dev) — the switch
lives in utils/spark_ops.py; ingestion is a host-side PythonOperator.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from utils.dag_docs import load_doc
from utils.spark_ops import (
    spark_submit,
    start_spark_cluster,
    stop_spark_cluster,
    wait_spark_ready,
)
from utils.tasks_utils import HomepediaETLTasks

DEFAULT_ARGS = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}

SILVER_BPE_APP = "/opt/homepedia/src/data_processing/transformations/bpe_etl.py"
SERVICES_GOLD_APP = (
    "/opt/homepedia/src/data_processing/transformations/services_gold.py"
)
QUALITY_APP = "/opt/homepedia/src/data_governance/quality/data_quality_reporter.py"
SERVICES_RULES = "/opt/homepedia/config/data_quality/gold_services.yaml"

tasks = HomepediaETLTasks()


with DAG(
    dag_id="amenities_etl_init",
    doc_md=load_doc("amenities"),
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["services", "bpe", "etl"],
    params={
        "year": Param(2024, type="integer", minimum=2014, maximum=2100),
        "departements": Param(None, type=["null", "array"], items={"type": "string"}),
    },
) as dag:
    start = EmptyOperator(task_id="start")

    ingest = PythonOperator(task_id="ingest_bpe", python_callable=tasks.ingest_bpe)

    # prepare spark cluster for job execution
    start_spark_vm = start_spark_cluster()
    wait_spark = wait_spark_ready()
    stop_spark_vm = stop_spark_cluster()

    bronze_to_silver_bpe = spark_submit(
        "bronze_to_silver_bpe", SILVER_BPE_APP + " --year {{ params.year }}"
    )

    services_to_gold = spark_submit(
        "services_to_gold",
        f"--conf spark.driver.memory=2g {SERVICES_GOLD_APP}",
    )

    # Quality gate on the served Gold table (read via JDBC).
    quality_check = spark_submit(
        "quality_check", f"{QUALITY_APP} --rules {SERVICES_RULES}"
    )

    end = EmptyOperator(task_id="end")

    start >> ingest
    start >> start_spark_vm >> wait_spark
    [ingest, wait_spark] >> bronze_to_silver_bpe >> services_to_gold >> quality_check
    quality_check >> stop_spark_vm >> end
