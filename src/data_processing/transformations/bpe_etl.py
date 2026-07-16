"""Silver ETL — INSEE BPE amenities (Bronze JSON -> Silver Parquet).

Flattens the DS_BPE cube to one row per commune × facility type: the count of
facilities of that type. Only leaf types are kept (FACILITY_TYPE like A101..),
within a real domain (FACILITY_DOM A..G, the _T total is dropped). The Gold job
pivots these into per-commune domain counts + key-amenity counts.

Run (inside the Spark container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/bpe_etl.py --year 2024
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

DATASET = "bpe"
SILVER_DATASET = "bpe"
LATEST_VINTAGE = 2024

DIMENSIONS_SCHEMA = StructType([
    StructField("GEO", StringType(), True),
    StructField("FACILITY_DOM", StringType(), True),
    StructField("FACILITY_SDOM", StringType(), True),
    StructField("FACILITY_TYPE", StringType(), True),
    StructField("TIME_PERIOD", StringType(), True),
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
BPE_SCHEMA = StructType([
    StructField("dataset", StringType(), True),
    StructField("year", LongType(), True),
    StructField("departement", StringType(), True),
    StructField("observations", ArrayType(OBSERVATION_SCHEMA), True),
])


def _bronze_input(
        bucket: str,
        year: int,
        departement: str | None
    ) -> str:
    """
    Build the S3 URI for the bronze BPE data.
    Args:
        bucket (str): The S3 bucket name.
        year (int): The year of the data.
        departement (str | None): The department code. If None,
        all departments are included.
    Returns:
        str: The S3 URI for the bronze BPE data.
    """
    if departement:
        return build_s3a_uri(
            bucket, f"{DATASET}/year={year}/departement={departement}/bpe.json"
        )
    return build_s3a_uri(bucket, f"{DATASET}/year={year}/departement=*/bpe.json")


def read_bronze(spark: SparkSession, path: str) -> DataFrame:
    return spark.read.option("multiline", True).schema(BPE_SCHEMA).json(path)


def transform(df: DataFrame) -> DataFrame:
    """
    Transform the raw BPE DataFrame into a flat table of counts per commune × facility type.
    Asserts that the input DataFrame has the expected schema and filters out
    rows with null observations.
    Args:
        df (DataFrame): The input DataFrame containing the raw BPE data.
    Returns:
        DataFrame: A transformed DataFrame with columns: code_insee, facility_dom, facility
    """
    return (
        df.filter(F.col("observations").isNotNull())
        .select(F.explode("observations").alias("o"), F.col("year"))
        .select(
            F.col("o.dimensions.GEO").alias("geo_code"),
            F.col("o.dimensions.FACILITY_DOM").alias("facility_dom"),
            F.col("o.dimensions.FACILITY_TYPE").alias("facility_type"),
            F.col("o.measures.OBS_VALUE_NIVEAU.value").alias("obs_value"),
            F.col("year"),
        )
        .filter(
            F.col("facility_dom").isin("A", "B", "C", "D", "E", "F", "G")
            & F.col("facility_type").rlike("^[A-G][0-9]")  # leaf types only
            & F.col("geo_code").rlike("(COM|ARM)-")
            & F.col("obs_value").isNotNull()
        )
        .withColumn(
            "code_insee",
            F.lpad(F.regexp_replace("geo_code", "^.*(COM|ARM)-", ""), 5, "0"),
        )
        .withColumn("nb", F.round("obs_value").cast("int"))
        .select("code_insee", "facility_dom", "facility_type", "nb", "year")
    )


def run(year: int, bronze_bucket: str, silver_bucket: str) -> None:
    spark = build_spark(f"homepedia-silver-bpe-{year}")
    spark.sparkContext.setLogLevel("WARN")

    actual_year = min(year, LATEST_VINTAGE)
    src = _bronze_input(bronze_bucket, actual_year, None)
    dst = build_s3a_uri(silver_bucket, SILVER_DATASET)
    print(f"[silver-bpe] read  {src}")

    raw = read_bronze(spark, src)
    silver = transform(raw)
    out = silver.count()
    print(f"[silver-bpe] rows={out}")
    silver.write.mode("overwrite").partitionBy("year").parquet(dst)
    print(f"[silver-bpe] wrote {out} rows to {dst}")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="INSEE BPE Bronze -> Silver ETL")
    parser.add_argument("--year", type=int, default=LATEST_VINTAGE)
    parser.add_argument(
        "--bronze-bucket", default=os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")
    )
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()
    run(args.year, args.bronze_bucket, args.silver_bucket)


if __name__ == "__main__":
    main()
