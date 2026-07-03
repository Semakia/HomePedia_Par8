"""HOMEPEDIA - Services / amenities ETL DAG (INSEE BPE).

Pipeline: ingest_bpe -> bronze_to_silver_bpe -> services_to_gold

INSEE BPE (Base Permanente des Équipements) -> Bronze S3, cleaned to Silver
(one row per commune × facility type), pivoted to the Gold `services` schema
(services.commune_equipements: counts by domain + key amenities + level).
Spark jobs run in the spark-master container via `docker exec`; ingestion is a
host-side PythonOperator. Task callables live in utils/tasks_utils.py.
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

SPARK_CONTAINER = "homepedia-dev-spark-master"
SILVER_BPE_APP = "/opt/homepedia/src/data_processing/transformations/bpe_etl.py"
SERVICES_GOLD_APP = (
    "/opt/homepedia/src/data_processing/transformations/services_gold.py"
)
QUALITY_APP = "/opt/homepedia/src/data_governance/quality/data_quality_reporter.py"
SERVICES_RULES = "/opt/homepedia/config/data_quality/gold_services.yaml"

tasks = HomepediaETLTasks()


with DAG(
    dag_id="amenities_etl",
    description="INSEE BPE local amenities (Bronze -> Silver -> Gold).",
    default_args=DEFAULT_ARGS,
    schedule="0 4 * * 1",  # weekly, Monday 04:00 (BPE is annual)
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

    bronze_to_silver_bpe = BashOperator(
        task_id="bronze_to_silver_bpe",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {SILVER_BPE_APP} "
            "--year {{ params.year }}\""
        ),
    )

    services_to_gold = BashOperator(
        task_id="services_to_gold",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' "
            f"--conf spark.driver.memory=1g {SERVICES_GOLD_APP}\""
        ),
    )

    # Quality gate on the served Gold table (read via JDBC).
    quality_check = BashOperator(
        task_id="quality_check",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} bash -c "
            f"\"spark-submit --master 'local[*]' {QUALITY_APP} "
            f"--rules {SERVICES_RULES}\""
        ),
    )

    end = EmptyOperator(task_id="end")

    (
        start >> ingest >> bronze_to_silver_bpe >> services_to_gold
        >> quality_check >> end
    )
