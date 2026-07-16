"""Silver ETL — SNCF stations (Bronze JSON -> Silver Parquet).

Joins the passenger-station referential (gares-de-voyageurs) with the annual
passenger counts (frequentation-gares) on the UIC code, producing one clean row
per station with its INSEE commune code, DRG segment, geo and latest traffic.

Run (inside the Spark container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/sncf_etl.py
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

DATASET = "sncf"
SILVER_DATASET = "sncf_gares"

GARE_SCHEMA = StructType([
    StructField("records", ArrayType(StructType([
        StructField("nom", StringType(), True),
        StructField("codes_uic", StringType(), True),
        StructField("codeinsee", StringType(), True),
        StructField("segment_drg", StringType(), True),
        StructField("position_geographique", StructType([
            StructField("lon", DoubleType(), True),
            StructField("lat", DoubleType(), True),
        ]), True),
    ])), True),
])

FREQ_SCHEMA = StructType([
    StructField("records", ArrayType(StructType([
        StructField("code_uic_complet", StringType(), True),
        StructField("total_voyageurs_2024", LongType(), True),
        StructField("total_voyageurs_2023", LongType(), True),
        StructField("total_voyageurs_2022", LongType(), True),
    ])), True),
])


def _read(spark: SparkSession, path: str, schema: StructType) -> DataFrame:
    raw = spark.read.option("multiline", True).schema(schema).json(path)
    return raw.select(F.explode("records").alias("r")).select("r.*")


def transform(gares: DataFrame, freq: DataFrame) -> DataFrame:
    # Latest available traffic per UIC (2024 -> 2023 -> 2022) + its year.
    freq = freq.select(
        F.col("code_uic_complet").alias("code_uic"),
        F.coalesce(
            "total_voyageurs_2024", "total_voyageurs_2023", "total_voyageurs_2022"
        ).cast("int").alias("frequentation"),
        F.when(F.col("total_voyageurs_2024").isNotNull(), F.lit(2024))
        .when(F.col("total_voyageurs_2023").isNotNull(), F.lit(2023))
        .when(F.col("total_voyageurs_2022").isNotNull(), F.lit(2022))
        .cast("short").alias("frequentation_year"),
    )

    # codes_uic / segment_drg can be multi-valued ("87001479;87271494", "A;A")
    # for stations spanning several UIC codes -> keep the primary (first) one.
    gares = gares.select(
        F.trim(F.split(F.col("codes_uic"), ";").getItem(0)).alias("code_uic"),
        F.col("nom").alias("nom_gare"),
        F.lpad(F.col("codeinsee"), 5, "0").alias("code_commune"),
        F.trim(F.split(F.col("segment_drg"), ";").getItem(0)).alias("segment_drg"),
        F.col("position_geographique.lon").alias("longitude"),
        F.col("position_geographique.lat").alias("latitude"),
    ).filter((F.col("code_uic").isNotNull()) & (F.col("code_uic") != ""))

    return gares.join(F.broadcast(freq), on="code_uic", how="left").dropDuplicates(
        ["code_uic"]
    )


def run(bronze_bucket: str, silver_bucket: str) -> None:
    spark = build_spark("homepedia-silver-sncf")
    spark.sparkContext.setLogLevel("WARN")

    gares = _read(spark, build_s3a_uri(bronze_bucket, f"{DATASET}/gares.json"), GARE_SCHEMA)
    freq = _read(spark, build_s3a_uri(bronze_bucket, f"{DATASET}/frequentation.json"), FREQ_SCHEMA)
    print(f"[silver-sncf] gares={gares.count()} freq={freq.count()}")

    silver = transform(gares, freq)
    out = silver.count()
    dst = build_s3a_uri(silver_bucket, SILVER_DATASET)
    silver.write.mode("overwrite").parquet(dst)
    print(f"[silver-sncf] wrote {out} stations to {dst}")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="SNCF Bronze -> Silver ETL")
    parser.add_argument(
        "--bronze-bucket", default=os.getenv("S3_BRONZE_BUCKET", "homepedia-bronze")
    )
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()
    run(args.bronze_bucket, args.silver_bucket)


if __name__ == "__main__":
    main()
