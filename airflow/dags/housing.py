"""HOMEPEDIA - main ETL DAG.

Pipeline: ingest -> bronze_to_silver -> silver_to_gold -> quality_checks -> refresh_cache

Task callables live in utils/tasks_utils.py; this module declares only the
variables and wires the DAG. DVF + INSEE + FiLoSoFi ingestion, Bronze->Silver
(the three sources), Silver->Gold and quality_checks are all real (Spark via
docker exec). Only refresh_cache is still a stub.

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
SILVER_FILOSOFI_APP = "/opt/homepedia/src/data_processing/transformations/filosofi_etl.py"
SILVER_DEMO_APP = "/opt/homepedia/src/data_processing/transformations/insee_demographics_etl.py"
GOLD_APP = "/opt/homepedia/src/data_processing/transformations/silver_to_gold.py"
QUALITY_APP = "/opt/homepedia/src/data_governance/quality/data_quality_reporter.py"
RULES_DIR = "/opt/homepedia/config/data_quality"

# Task callables grouped in one object; bound methods are passed to the operators.
tasks = HomepediaETLTasks()


with DAG(
    dag_id="housing_etl",
    description="Main HOMEPEDIA batch pipeline (Bronze -> Silver -> Gold).",
    default_args=DEFAULT_ARGS,
    schedule="0 2 * * *",  # daily at 02:00
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["housing", "etl"],
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

    # Ingest Bronze data from the dvf source into S3.
    ingest_from_dvf = PythonOperator(
        task_id="ingest_from_dvf",
        python_callable=tasks.ingest_dvf,
    )
    # Ingest Bronze data from the insee source into S3.
    ingest_from_insee = PythonOperator(
        task_id="ingest_from_insee",
        python_callable=tasks.ingest_insee,
    )
    # Ingest Bronze data from the filosofi source into S3.
    ingest_from_filosofi = PythonOperator(
        task_id="ingest_from_filosofi",
        python_callable=tasks.ingest_filosofi,
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

    # Spark job: clean FiLoSoFi Bronze -> Silver Parquet (income caps at 2023).
    bronze_to_silver_filosofi = BashOperator(
        task_id="bronze_to_silver_filosofi",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {SILVER_FILOSOFI_APP} "
            "--year {{ params.year }}\""
        ),
    )

    # Spark job: INSEE Bronze -> Silver demographics (age x sex breakdown).
    bronze_to_silver_demographics = BashOperator(
        task_id="bronze_to_silver_demographics",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {SILVER_DEMO_APP} "
            "--year {{ params.year }}\""
        ),
    )

    # Spark JDBC job: join DVF x INSEE x FiLoSoFi Silver -> 3 Gold tables.
    # Runs in spark-master (Postgres driver baked in the image); POSTGRES_* come
    # from the container's .env (env_file), pointing at the remote Gold DB.
    silver_to_gold = BashOperator(
        task_id="silver_to_gold",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' "
            f"--conf spark.driver.memory=1g "
            f"--conf spark.sql.shuffle.partitions=8 {GOLD_APP}\""
        ),
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

    # Gold quality gates: read the served Postgres tables via JDBC.
    quality_gold_market = BashOperator(
        task_id="quality_gold_market",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {QUALITY_APP} "
            f"--rules {RULES_DIR}/gold_market.yaml\""
        ),
    )
    quality_gold_demographics = BashOperator(
        task_id="quality_gold_demographics",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {QUALITY_APP} "
            f"--rules {RULES_DIR}/gold_demographics.yaml\""
        ),
    )

    refresh_cache = PythonOperator(
        task_id="refresh_cache",
        python_callable=tasks.refresh_cache,
    )

    end = EmptyOperator(task_id="end")

    # Wire DAG dependencies
    start >> [ingest_from_dvf, ingest_from_insee, ingest_from_filosofi]
    ingest_from_dvf >> bronze_to_silver_dvf
    ingest_from_insee >> [bronze_to_silver_insee, bronze_to_silver_demographics]
    ingest_from_filosofi >> bronze_to_silver_filosofi
    [
        bronze_to_silver_dvf,
        bronze_to_silver_insee,
        bronze_to_silver_filosofi,
        bronze_to_silver_demographics,
    ] >> silver_to_gold
    silver_to_gold >> [
        quality_checks,
        quality_gold_market,
        quality_gold_demographics,
    ] >> refresh_cache >> end
