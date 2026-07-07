"""HOMEPEDIA - Mobility ETL DAG (SNCF train-station accessibility).

Pipeline: ingest_sncf -> bronze_to_silver_sncf -> mobility_to_gold -> quality
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
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

SILVER_SNCF_APP = "/opt/homepedia/src/data_processing/transformations/sncf_etl.py"
MOBILITY_GOLD_APP = (
    "/opt/homepedia/src/data_processing/transformations/mobility_gold.py"
)
QUALITY_APP = "/opt/homepedia/src/data_governance/quality/data_quality_reporter.py"
MOBILITY_RULES = "/opt/homepedia/config/data_quality/gold_mobility.yaml"

# Task callables grouped in one object; bound methods are passed to operators.
tasks = HomepediaETLTasks()


with DAG(
    dag_id="mobility_etl_init",
    doc_md=load_doc("mobility"),
    default_args=DEFAULT_ARGS,
    schedule_interrval=None,
    catchup=False,
    tags=["mobility", "sncf", "etl"],
) as dag:
    start = EmptyOperator(task_id="start")

    ingest = PythonOperator(
        task_id="ingest_sncf", python_callable=tasks.ingest_sncf
    )

    start_spark_vm = start_spark_cluster()
    wait_spark = wait_spark_ready()
    stop_spark_vm = stop_spark_cluster()

    bronze_to_silver_sncf = spark_submit("bronze_to_silver_sncf", SILVER_SNCF_APP)

    mobility_to_gold = spark_submit(
        "mobility_to_gold",
        f"--conf spark.driver.memory=2g {MOBILITY_GOLD_APP}",
    )

    quality_check = spark_submit(
        "quality_check", f"{QUALITY_APP} --rules {MOBILITY_RULES}"
    )

    end = EmptyOperator(task_id="end")

    start >> ingest
    start >> start_spark_vm >> wait_spark
    [ingest, wait_spark] >> bronze_to_silver_sncf >> mobility_to_gold >> quality_check
    quality_check >> stop_spark_vm >> end
