"""Silver ETL — INSEE demographics (age x sex) from the population Bronze.

The INSEE Bronze cube already carries the full SEX x AGE breakdown; the main
insee_etl only keeps the SEX=_T & AGE=_T total. This job keeps the breakdown for
demographic segmentation: one row per commune x year x sex x (disjoint) age band.

Disjoint age bands (cover the whole population without overlap; the cube also
exposes overlapping aggregates like Y_LT20/Y20T64/Y_GE65 which we drop):
    Y_LT15, Y15T24, Y25T39, Y40T54, Y55T64, Y65T79, Y_GE80

Run (inside the Spark container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/insee_demographics_etl.py \
        --year 2022
"""

from __future__ import annotations

import argparse
import os

from pyspark.sql import functions as F
from src.data_processing.transformations.insee_etl import (
    _bronze_input,
    read_bronze,
)
from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark

DATASET = "insee"
SILVER_DATASET = "insee_demographics"
LATEST_VINTAGE = 2022
DISJOINT_AGES = [
    "Y_LT15", "Y15T24", "Y25T39", "Y40T54", "Y55T64", "Y65T79", "Y_GE80",
]


def run(
    year: int,
    bronze_bucket: str,
    silver_bucket: str
) -> None:
    spark = build_spark(f"homepedia-silver-insee-demo-{year}")
    spark.sparkContext.setLogLevel("WARN")

    actual_year = min(year, LATEST_VINTAGE)
    src = _bronze_input(bronze_bucket, actual_year, None)
    dst = build_s3a_uri(silver_bucket, SILVER_DATASET)
    print(f"[silver-insee-demo] read  {src}")

    raw = read_bronze(spark, src)
    demo = (
        raw.filter(F.col("observations").isNotNull())
        .select(F.explode("observations").alias("o"), F.col("year"))
        .select(
            F.col("o.dimensions.GEO").alias("geo_code"),
            F.col("o.dimensions.SEX").alias("sex"),
            F.col("o.dimensions.AGE").alias("age_band"),
            F.col("o.measures.OBS_VALUE_NIVEAU.value").alias("obs_value"),
            F.col("year"),
        )
        .filter(
            F.col("sex").isin("F", "M", "_T")
            & F.col("age_band").isin(DISJOINT_AGES)
            & F.col("geo_code").rlike("(COM|ARM)-")
        )
        .withColumn(
            "code_insee",
            F.lpad(F.regexp_replace("geo_code", "^.*(COM|ARM)-", ""), 5, "0"),
        )
        .withColumn("population", F.round("obs_value").cast("int"))
        .select("code_insee", "sex", "age_band", "population", "year")
    )

    out_count = demo.count()
    print(f"[silver-insee-demo] rows={out_count}")
    demo.write.mode("overwrite").partitionBy("year").parquet(dst)
    print(f"[silver-insee-demo] wrote {out_count} rows to {dst}")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="INSEE demographics Silver ETL")
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
