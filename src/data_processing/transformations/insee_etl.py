"""Silver ETL — INSEE population (Bronze JSON -> Silver Parquet).

Cleans and normalizes the INSEE referential and population data.
Key steps:
- Reads the raw JSON files from the Bronze layer.
- Extracts and flattens both the commune metadata and population observations.
- Cleans and normalizes commune codes (stripping prefixes, padding to 5 characters).
- Joins the populations to the commune referential.
- Writes the result to the Silver layer in Parquet format, partitioned by year and department.

Run (inside the Spark container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/insee_etl.py \
        --year 2022 --departement 01
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request

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

DATASET = "insee"

COMMUNE_SCHEMA = StructType([
    StructField("code", StringType(), True),
    StructField("nom", StringType(), True),
    StructField("codeDepartement", StringType(), True),
    StructField("codeRegion", StringType(), True),
])

# INSEE Melodi observations are a cube: dimensions (GEO/SEX/AGE/...) + nested
# measures. GEO looks like "2025-COM-01053"; the total population for a commune
# is the SEX=_T & AGE=_T cell, read from measures.OBS_VALUE_NIVEAU.value.
DIMENSIONS_SCHEMA = StructType([
    StructField("GEO", StringType(), True),
    StructField("SEX", StringType(), True),
    StructField("AGE", StringType(), True),
    StructField("RP_MEASURE", StringType(), True),
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

INSEE_SCHEMA = StructType([
    StructField("dataset", StringType(), True),
    StructField("year", LongType(), True),
    StructField("departement", StringType(), True),
    StructField("communes", ArrayType(COMMUNE_SCHEMA), True),
    StructField("observations", ArrayType(OBSERVATION_SCHEMA), True),
])

GEO_API_URLS = (
    "https://geo.api.gouv.fr/communes"
    "?fields=code,nom,codeDepartement,codeRegion",
    "https://geo.api.gouv.fr/communes?type=arrondissement-municipal"
    "&fields=code,nom,codeDepartement,codeRegion",
)


def _bronze_input(
    bucket: str,
    year: int,
    departement: str | None
) -> str:
    if departement:
        return build_s3a_uri(bucket, f"{DATASET}/year={year}/departement={departement}/population.json")
    return build_s3a_uri(bucket, f"{DATASET}/year={year}/departement=*/population.json")


def read_bronze(
    spark: SparkSession,
    path: str
) -> DataFrame:
    # Read multiline JSON with explicit schema to handle legacy files missing 'communes'
    return spark.read.option("multiline", True).schema(INSEE_SCHEMA).json(path)


def _fetch_referential(spark: SparkSession, df: DataFrame) -> DataFrame:
    """Build the commune + arrondissement referential from geo.api.

    geo.api is authoritative and uniform; the Bronze `communes` field is only
    used as a fallback if the API is unreachable.
    """
    try:
        rows: list[dict] = []
        for url in GEO_API_URLS:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows.extend(json.loads(resp.read().decode("utf-8")))
        referential = spark.createDataFrame(rows, schema=COMMUNE_SCHEMA)
        print(f"[silver-insee] referential from geo.api: {len(rows)} entries")
    except Exception as e:
        print(f"[silver-insee] geo.api referential failed ({e}); using Bronze.")
        referential = (
            df.filter(F.col("communes").isNotNull())
            .select(F.explode("communes").alias("c"))
            .select("c.*")
        )
    return (
        referential.select(
            F.lpad(F.col("code"), 5, "0").alias("code_insee"),
            F.col("nom").alias("nom_commune"),
            F.col("codeDepartement").alias("code_departement"),
            F.col("codeRegion").alias("code_region"),
        )
        .dropDuplicates(["code_insee"])
    )


def transform(
    df: DataFrame,
    spark: SparkSession
) -> DataFrame:
    """
    Transform and normalize the raw INSEE JSON data.
    Separates the communes metadata and the observations to prevent cross-joins.
    """
    # 1. Commune + arrondissement referential from geo.api (authoritative).
    #    The Bronze `communes` field is inconsistent across vintages (legacy
    #    files store none), so we don't rely on it; geo.api gives a complete,
    #    uniform referential including the municipal arrondissements needed to
    #    resolve Paris/Lyon/Marseille ARM- observations.
    communes_df = _fetch_referential(spark, df)

    # 2. Extract observations -> total population per commune.
    #    Keep the SEX=_T & AGE=_T cell (the commune total), commune-level GEO only.
    obs_df = (
        df.filter(F.col("observations").isNotNull())
        .select(F.explode("observations").alias("o"), F.col("year"))
        .select(
            F.col("o.dimensions.GEO").alias("geo_code"),
            F.col("o.dimensions.SEX").alias("sex"),
            F.col("o.dimensions.AGE").alias("age"),
            F.col("o.measures.OBS_VALUE_NIVEAU.value").alias("obs_value"),
            F.col("year"),
        )
        .filter(
            (F.col("sex") == "_T")
            & (F.col("age") == "_T")
            & F.col("geo_code").rlike("(COM|ARM)-")
        )
        # GEO = "<year>-COM-<insee>" or "-ARM-<insee>" (Paris/Lyon/Marseille
        # arrondissements) -> strip everything up to and incl. "COM-"/"ARM-".
        .withColumn("code_insee", F.lpad(F.regexp_replace("geo_code", "^.*(COM|ARM)-", ""), 5, "0"))
        .withColumn("population", F.round("obs_value").cast("int"))
        .select("code_insee", "population", "year")
    )

    # 3. Join the metadata with the population counts using broadcast to avoid shuffle
    joined_df = obs_df.join(F.broadcast(communes_df), on="code_insee", how="inner").select(
        "code_insee",
        "nom_commune",
        "code_departement",
        "code_region",
        "population",
        "year"
    )

    return joined_df


def run(
    year: int,
    departement: str | None,
    bronze_bucket: str,
    silver_bucket: str
) -> None:
    """
    Run the INSEE Bronze -> Silver ETL.
    """
    spark = build_spark(f"homepedia-silver-insee-{year}")
    spark.sparkContext.setLogLevel("WARN")

    # Melodi API contains data up to 2022. Fallback to 2022 if a later year is requested.
    actual_year = min(year, 2022)
    if year > 2022:
        print(f"[silver-insee] Requested year {year} is greater than 2022. Falling back to Bronze year {actual_year}.")

    src_path = _bronze_input(bronze_bucket, actual_year, departement)
    dst_path = build_s3a_uri(silver_bucket, DATASET)
    print(f"[silver-insee] read  {src_path}")

    raw = read_bronze(spark, src_path)
    raw_count = raw.count()
    print(f"[silver-insee] read {raw_count} raw department records")

    silver = transform(raw, spark)
    out_count = silver.count()

    print(f"[silver-insee] records after transformation={out_count}")
    (
        silver.write.mode("overwrite")
        .partitionBy("year", "code_departement")
        .parquet(dst_path)
    )
    print(f"[silver-insee] wrote {out_count} rows to {dst_path}")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="INSEE Bronze -> Silver ETL")
    parser.add_argument("--year", type=int, required=True)
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
