"""HOMEPEDIA - main ETL DAG.

Pipeline: ingest -> bronze_to_silver -> silver_to_gold -> quality_checks -> refresh_cache

Task callables live in utils/tasks_utils.py; this module declares only the
variables and wires the DAG. DVF ingestion + Bronze->Silver Spark are real;
Gold/quality/cache and INSEE ingestion are still stubs.

Trigger with config, e.g. { "year": 2024, "departements": ["75", "69"] }.
Default (empty `departements`) ingests every code in utils/departements.json.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
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

# Silver Spark job runs inside the running spark-master container (Spark runtime
# + S3A jars live there). Airflow only `docker exec`s into it.
SPARK_CONTAINER = "homepedia-dev-spark-master"
SILVER_DVF_APP = "/opt/homepedia/src/data_processing/transformations/housing_dvf_etl.py"
SILVER_INSEE_APP = "/opt/homepedia/src/data_processing/transformations/insee_etl.py"
QUALITY_APP = "/opt/homepedia/src/data_governance/quality/data_quality_reporter.py"

# Task callables grouped in one object; bound methods are passed to the operators.
tasks = HomepediaETLTasks()


with DAG(
    dag_id="homepedia_etl",
    description="Main HOMEPEDIA batch pipeline (Bronze -> Silver -> Gold).",
    default_args=DEFAULT_ARGS,
    schedule="0 2 * * *",  # daily at 02:00
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["homepedia", "etl"],
    params={
        "year": Param(2024, type="integer", minimum=2014, maximum=2100),
        # Nullable so the UI field is OPTIONAL (no red asterisk / no "required").
        # Leave empty -> every departement in utils/departements.json; or pass a
        # subset, e.g. ["75", "69"].
        "departements": Param(
            None,
            type=["null", "array"],
            items={"type": "string"},
        ),
    },
) as dag:
    start = EmptyOperator(task_id="start")

    ingest_from_dvf = PythonOperator(
        task_id="ingest_from_dvf",
        python_callable=tasks.ingest_dvf,
    )

    ingest_from_insee = PythonOperator(
        task_id="ingest_from_insee",
        python_callable=tasks.ingest_insee,
    )

    # Spark job: clean DVF Bronze -> Silver Parquet for the whole year
    bronze_to_silver_dvf = BashOperator(
        task_id="bronze_to_silver_dvf",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {SILVER_DVF_APP} "
            "--year {{ params.year }}\""
        ),
    )

    # Spark job: clean INSEE Bronze -> Silver Parquet for the whole year
    bronze_to_silver_insee = BashOperator(
        task_id="bronze_to_silver_insee",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {SILVER_INSEE_APP} "
            "--year {{ params.year }}\""
        ),
    )

    silver_to_gold = PythonOperator(
        task_id="silver_to_gold",
        python_callable=tasks.silver_to_gold,
    )

    # Data-quality gate on the Silver layer (fails the task if a critical rule
    # breaks). Runs the Spark job in the spark-master container, same as Silver.
    quality_checks = BashOperator(
        task_id="quality_checks",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {QUALITY_APP} --dataset dvf\""
        ),
    )

    refresh_cache = PythonOperator(
        task_id="refresh_cache",
        python_callable=tasks.refresh_cache,
    )

    end = EmptyOperator(task_id="end")

    # Wire DAG dependencies
    start >> [ingest_from_dvf, ingest_from_insee]
    ingest_from_dvf >> bronze_to_silver_dvf
    ingest_from_insee >> bronze_to_silver_insee
    [bronze_to_silver_dvf, bronze_to_silver_insee] >> silver_to_gold >> quality_checks >> refresh_cache >> end
