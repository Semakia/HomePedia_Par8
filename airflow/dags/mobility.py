"""HOMEPEDIA - Mobility ETL DAG (SNCF train-station accessibility).

Pipeline: ingest_sncf -> bronze_to_silver_sncf -> mobility_to_gold

SNCF open data (gares-de-voyageurs + frequentation-gares) -> Bronze S3, cleaned
to Silver (one row per station), aggregated to the Gold `mobility` schema
(mobility.gares + mobility.commune_transport). Spark jobs run in the spark-master
container via `docker exec`; ingestion is a host-side PythonOperator.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from utils.tasks_utils import HomepediaETLTasks

DEFAULT_ARGS = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}

SPARK_CONTAINER = "homepedia-dev-spark-master"
SILVER_SNCF_APP = "/opt/homepedia/src/data_processing/transformations/sncf_etl.py"
MOBILITY_GOLD_APP = (
    "/opt/homepedia/src/data_processing/transformations/mobility_gold.py"
)
QUALITY_APP = "/opt/homepedia/src/data_governance/quality/data_quality_reporter.py"
MOBILITY_RULES = "/opt/homepedia/config/data_quality/gold_mobility.yaml"

# Task callables grouped in one object; bound methods are passed to operators.
tasks = HomepediaETLTasks()


with DAG(
    dag_id="mobility_etl",
    description="SNCF train-station accessibility (Bronze -> Silver -> Gold).",
    default_args=DEFAULT_ARGS,
    schedule="0 3 * * 1",  # weekly, Monday 03:00 (referential changes slowly)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mobility", "sncf", "etl"],
) as dag:
    start = EmptyOperator(task_id="start")

    ingest = PythonOperator(
        task_id="ingest_sncf", python_callable=tasks.ingest_sncf
    )

    bronze_to_silver_sncf = BashOperator(
        task_id="bronze_to_silver_sncf",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {SILVER_SNCF_APP}\""
        ),
    )

    mobility_to_gold = BashOperator(
        task_id="mobility_to_gold",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' "
            f"--conf spark.driver.memory=1g {MOBILITY_GOLD_APP}\""
        ),
    )

    quality_check = BashOperator(
        task_id="quality_check",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {QUALITY_APP} "
            f"--rules {MOBILITY_RULES}\""
        ),
    )

    end = EmptyOperator(task_id="end")

    (
        start >> ingest >> bronze_to_silver_sncf >> mobility_to_gold
        >> quality_check >> end
    )
