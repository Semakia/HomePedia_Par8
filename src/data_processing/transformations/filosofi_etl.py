"""Silver ETL — INSEE FiLoSoFi income (Bronze JSON -> Silver Parquet).

Reads the raw FiLoSoFi cube landed in Bronze and keeps the headline indicator:
the median standard of living per commune (FILOSOFI_MEASURE=MED_SL, in EUR_YR).
That is the "revenu médian" used downstream for the affordability metric.

Output: one row per commune (code_insee, revenu_median, year), partitioned by
year and code_departement, written to s3://<silver>/filosofi.

Run (inside the Spark container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/filosofi_etl.py --year 2023
"""

from __future__ import annotations

import argparse
import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)
from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark

DATASET = "filosofi"
# FiLoSoFi commune vintage caps at 2023 (published with a lag).
LATEST_VINTAGE = 2023
# Headline indicator: median standard of living, euros per year.
INCOME_MEASURE = "MED_SL"
INCOME_UNIT = "EUR_YR"

COMMUNE_SCHEMA = StructType([
    StructField("code", StringType(), True),
    StructField("nom", StringType(), True),
    StructField("codeDepartement", StringType(), True),
    StructField("codeRegion", StringType(), True),
])

# FiLoSoFi observations: a cube keyed by GEO ("YYYY-COM-xxxxx"), TIME_PERIOD,
# UNIT_MEASURE and FILOSOFI_MEASURE; value in measures.OBS_VALUE_NIVEAU.value.
DIMENSIONS_SCHEMA = StructType([
    StructField("GEO", StringType(), True),
    StructField("TIME_PERIOD", StringType(), True),
    StructField("UNIT_MEASURE", StringType(), True),
    StructField("FILOSOFI_MEASURE", StringType(), True),
])

MEASURES_SCHEMA = StructType([
    StructField(
        "OBS_VALUE_NIVEAU",
        StructType([StructField("value", DoubleType(), True)]),
        True,
    ),
])

OBSERVATION_SCHEMA = StructType([
    StructField("dimensions", DIMENSIONS_SCHEMA, True),
    StructField("measures", MEASURES_SCHEMA, True),
])

FILOSOFI_SCHEMA = StructType([
    StructField("dataset", StringType(), True),
    StructField("year", LongType(), True),
    StructField("departement", StringType(), True),
    StructField("communes", ArrayType(COMMUNE_SCHEMA), True),
    StructField("observations", ArrayType(OBSERVATION_SCHEMA), True),
])


def _bronze_input(
    bucket: str,
    year: int,
    departement: str | None
) -> str:
    """
    Bronze FiLoSoFi JSON input path for the given year and departement.
    If departement is None, returns a wildcard path for all departements.
    Args:
        bucket: S3 bucket name (e.g. "homepedia-bronze").
        year: DVF year (e.g. 2023).
        departement: departement code (e.g. "75") or None for all departements.
    Returns:
        S3 path to the FiLoSoFi JSON files in Bronze.
    """
    if departement:
        return build_s3a_uri(
            bucket, f"{DATASET}/year={year}/departement={departement}/filosofi.json"
        )
    return build_s3a_uri(bucket, f"{DATASET}/year={year}/departement=*/filosofi.json")


def read_bronze(
    spark: SparkSession,
    path: str
) -> DataFrame:
    """
    Read the bronze FiLoSoFi JSON files into a Spark DataFrame.
    Args:
        spark: Spark session.
        path: S3 path to the FiLoSoFi JSON files in Bronze.
    Returns:
        Spark DataFrame containing the FiLoSoFi data.
    """
    return spark.read.option("multiline", True).schema(FILOSOFI_SCHEMA).json(path)


def transform(
    df: DataFrame
) -> DataFrame:
    """
    Keep the median standard of living (MED_SL / EUR_YR) per commune.
    Args:
        df: Spark DataFrame containing the FiLoSoFi data.
    Returns:
        Spark DataFrame with columns: code_insee, code_departement, revenu_median,
        year."""
    # Commune referential -> code_departement for partitioning.
    communes_df = (
        df.filter(F.col("communes").isNotNull())
        .select(F.explode("communes").alias("c"))
        .select(
            F.lpad(F.col("c.code"), 5, "0").alias("code_insee"),
            F.col("c.codeDepartement").alias("code_departement"),
        )
        .dropDuplicates(["code_insee"])
    )

    obs_df = (
        df.filter(F.col("observations").isNotNull())
        .select(F.explode("observations").alias("o"), F.col("year"))
        .select(
            F.col("o.dimensions.GEO").alias("geo_code"),
            F.col("o.dimensions.FILOSOFI_MEASURE").alias("measure"),
            F.col("o.dimensions.UNIT_MEASURE").alias("unit"),
            F.col("o.measures.OBS_VALUE_NIVEAU.value").alias("obs_value"),
            F.col("year"),
        )
        .filter(
            (F.col("measure") == INCOME_MEASURE)
            & (F.col("unit") == INCOME_UNIT)
            & F.col("geo_code").rlike("(COM|ARM)-")
            & F.col("obs_value").isNotNull()
        )
        # GEO = "<ref>-COM-<insee>" or "-ARM-<insee>" (arrondissements) -> strip
        # everything up to and incl. "COM-"/"ARM-".
        .withColumn("code_insee", F.lpad(F.regexp_replace("geo_code", "^.*(COM|ARM)-", ""), 5, "0"))
        .withColumn("revenu_median", F.round("obs_value", 2))
        .select("code_insee", "revenu_median", "year")
    )

    return obs_df.join(F.broadcast(communes_df), on="code_insee", how="left").select(
        "code_insee",
        "code_departement",
        "revenu_median",
        "year",
    )


def run(
    year: int,
    departement: str | None,
    bronze_bucket: str,
    silver_bucket: str
) -> None:
    """
    Run the FiLoSoFi Bronze -> Silver ETL.
    Args:
        year: DVF year (e.g. 2023).
        departement: departement code (e.g. "75") or None for all departements.
        bronze_bucket: S3 bucket name for bronze data (e.g. "homepedia-bronze").
        silver_bucket: S3 bucket name for silver data (e.g. "homepedia-silver").
    """
    spark = build_spark(f"homepedia-silver-filosofi-{year}")
    spark.sparkContext.setLogLevel("WARN")

    actual_year = min(year, LATEST_VINTAGE)
    if year > LATEST_VINTAGE:
        print(
            f"[silver-filosofi] requested {year} > {LATEST_VINTAGE}; "
            f"falling back to Bronze year {actual_year}."
        )

    src_path = _bronze_input(bronze_bucket, actual_year, departement)
    dst_path = build_s3a_uri(silver_bucket, DATASET)
    print(f"[silver-filosofi] read  {src_path}")

    raw = read_bronze(spark, src_path)
    print(f"[silver-filosofi] read {raw.count()} raw department records")

    silver = transform(raw)
    out_count = silver.count()
    print(f"[silver-filosofi] records after transformation={out_count}")

    (
        silver.write.mode("overwrite")
        .partitionBy("year", "code_departement")
        .parquet(dst_path)
    )
    print(f"[silver-filosofi] wrote {out_count} rows to {dst_path}")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="FiLoSoFi Bronze -> Silver ETL")
    parser.add_argument("--year", type=int, default=LATEST_VINTAGE)
    parser.add_argument("--departement", type=str, default=None)
    parser.add_argument(
        "--bronze-bucket", default=os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")
    )
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()
    run(args.year, args.departement, args.bronze_bucket, args.silver_bucket)


if __name__ == "__main__":
    main()
