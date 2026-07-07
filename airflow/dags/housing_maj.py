"""HOMEPEDIA - main ETL DAG.

Pipeline: ingest -> bronze_to_silver -> silver_to_gold -> quality -> refresh_cache
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
    dag_id="housing_etl_maj",
    doc_md=load_doc("housing"),
    default_args=DEFAULT_ARGS,
    schedule="0 0 1 * *",  # monthly, 1st of month at 00:00
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

    # On-demand Spark VM lifecycle (no-ops in dev). Started in parallel with the
    # ingestion so it is warm by the time the Silver jobs need it.
    start_spark_vm = start_spark_cluster()
    wait_spark = wait_spark_ready()
    stop_spark_vm = stop_spark_cluster()

    # Spark job: clean DVF Bronze -> Silver Parquet for the whole year. This is
    # the heaviest transform (whole-France) -> give the local[*] driver 4g of the
    bronze_to_silver_dvf = spark_submit(
        "bronze_to_silver_dvf",
        "--conf spark.driver.memory=4g " + SILVER_DVF_APP + " --year {{ params.year }}",
    )

    # Spark job: clean INSEE Bronze -> Silver Parquet for the whole year.
    bronze_to_silver_insee = spark_submit(
        "bronze_to_silver_insee", SILVER_INSEE_APP + " --year {{ params.year }}"
    )

    # Spark job: clean FiLoSoFi Bronze -> Silver Parquet (income caps at 2023).
    bronze_to_silver_filosofi = spark_submit(
        "bronze_to_silver_filosofi", SILVER_FILOSOFI_APP + " --year {{ params.year }}"
    )

    # Spark job: INSEE Bronze -> Silver demographics (age x sex breakdown).
    bronze_to_silver_demographics = spark_submit(
        "bronze_to_silver_demographics", SILVER_DEMO_APP + " --year {{ params.year }}"
    )

    # Spark JDBC job: join DVF x INSEE x FiLoSoFi Silver -> 3 Gold tables. The
    # Postgres driver is baked in the spark image; POSTGRES_* come from the VM's
    # .env, pointing at the remote Gold DB on the VPS.
    silver_to_gold = spark_submit(
        "silver_to_gold",
        f"--conf spark.driver.memory=3g --conf spark.sql.shuffle.partitions=8 {GOLD_APP}",
    )

    # Data-quality gate on the Silver layer (fails the task if a critical rule
    # breaks).
    quality_checks = spark_submit("quality_checks", f"{QUALITY_APP} --dataset dvf")

    # Gold quality gates: read the served Postgres tables via JDBC.
    quality_gold_market = spark_submit(
        "quality_gold_market", f"{QUALITY_APP} --rules {RULES_DIR}/gold_market.yaml"
    )

    quality_gold_demographics = spark_submit(
        "quality_gold_demographics",
        f"{QUALITY_APP} --rules {RULES_DIR}/gold_demographics.yaml",
    )

    refresh_cache = PythonOperator(
        task_id="refresh_cache",
        python_callable=tasks.refresh_cache,
    )

    end = EmptyOperator(task_id="end")

    # Wire DAG dependencies.
    # Ingestion is host-side (PythonOperator on the Airflow worker) and cheap, so
    # it stays parallel and the VM warms up alongside it.
    start >> [ingest_from_dvf, ingest_from_insee, ingest_from_filosofi]
    start >> start_spark_vm >> wait_spark

    # All Spark jobs share ONE on-demand VM running `spark-submit --master local[*]`.
    # Run them STRICTLY ONE AT A TIME: several local Spark drivers at once stack
    # their heap and OOM the VM.
    [wait_spark, ingest_from_dvf] >> bronze_to_silver_dvf
    [bronze_to_silver_dvf, ingest_from_insee] >> bronze_to_silver_insee
    bronze_to_silver_insee >> bronze_to_silver_demographics
    [bronze_to_silver_demographics, ingest_from_filosofi] >> bronze_to_silver_filosofi
    bronze_to_silver_filosofi >> silver_to_gold

    # Quality gates hit the VM over JDBC too -> keep them serial as well.
    silver_to_gold >> quality_checks >> quality_gold_market >> quality_gold_demographics

    quality_gold_demographics >> refresh_cache
    quality_gold_demographics >> stop_spark_vm
    [refresh_cache, stop_spark_vm] >> end
