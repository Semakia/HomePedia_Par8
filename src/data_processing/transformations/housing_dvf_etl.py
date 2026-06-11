"""Silver ETL — DVF housing (Bronze CSV.gz -> Silver Parquet).

Cleans raw DVF transactions into a reliable price/m² dataset. The logic is
specified in docs/silver_dvf_logic.md. Key trap handled: in DVF, one mutation
spans several rows with the SAME valeur_fonciere repeated, so price/m² must be
reasoned at mutation level — here via the "mono-bien" filter (keep mutations
with exactly one residential local).

Run (inside the Spark container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/housing_dvf_etl.py \
        --year 2024 --departement 90
Omit --departement to process every departement landed for that year.
"""

from __future__ import annotations

import argparse
import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark

DATASET = "dvf"
HABITABLE = ["Maison", "Appartement"]

# Anti-aberrant bounds.
MIN_SURFACE = 9.0
PRICE_M2_MIN = 500.0
PRICE_M2_MAX = 20_000.0

FINAL_COLUMNS = [
    "id_mutation",
    "date_mutation",
    "year",
    "month",
    "code_commune",
    "code_departement",
    "nom_commune",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "valeur_fonciere",
    "prix_m2",
    "longitude",
    "latitude",
]


def _bronze_input(
    bucket: str,
    year: int,
    departement: str | None
) -> str:
    if departement:
        return build_s3a_uri(bucket, f"{DATASET}/year={year}/departement={departement}/*.csv.gz")
    return build_s3a_uri(bucket, f"{DATASET}/year={year}/departement=*/*.csv.gz")


def read_bronze(
    spark: SparkSession,
    path: str
) -> DataFrame:
    return (
        spark.read.option("header", True)
        .option("sep", ",")
        .option("encoding", "UTF-8")
        .option("quote", '"')
        .option("escape", '"')
        .csv(path)
    )


def transform(
    df: DataFrame
) -> DataFrame:
    """
    Apply the documented DVF cleaning pipeline -> one row per sold dwelling.
    Args:
      - df: raw DVF DataFrame, as read from the Bronze CSV.gz
    """
    # 1-2. Sales of residential locals only.
    df = df.filter(F.col("nature_mutation") == "Vente").filter(
        F.col("type_local").isin(HABITABLE)
    )

    # Cast numerics (raw is all strings).
    df = (
        df.withColumn("valeur_fonciere", F.col("valeur_fonciere").cast("double"))
        .withColumn("surface_reelle_bati", F.col("surface_reelle_bati").cast("double"))
        .withColumn(
            "nombre_pieces_principales", F.col("nombre_pieces_principales").cast("int")
        )
        .withColumn("longitude", F.col("longitude").cast("double"))
        .withColumn("latitude", F.col("latitude").cast("double"))
    )

    # 3. Mono-bien: keep mutations with exactly one residential local, so the
    #    repeated valeur_fonciere maps to a single surface (reliable price/m²).
    per_mutation = Window.partitionBy("id_mutation")
    df = (
        df.withColumn("_nb_hab", F.count("*").over(per_mutation))
        .filter(F.col("_nb_hab") == 1)
        .drop("_nb_hab")
    )

    # 4. Sane surface / value.
    df = df.filter(
        (F.col("surface_reelle_bati") > MIN_SURFACE) & (F.col("valeur_fonciere") > 0)
    )

    # 5-6. Price per m² within plausible bounds.
    df = df.withColumn(
        "prix_m2", F.round(F.col("valeur_fonciere") / F.col("surface_reelle_bati"), 2)
    ).filter((F.col("prix_m2") >= PRICE_M2_MIN) & (F.col("prix_m2") <= PRICE_M2_MAX))

    # 7-9. Normalize INSEE code, derive dates, dedup.
    df = (
        df.withColumn("code_commune", F.lpad(F.col("code_commune"), 5, "0"))
        .withColumn("date_mutation", F.to_date("date_mutation", "yyyy-MM-dd"))
        .withColumn("year", F.year("date_mutation"))
        .withColumn("month", F.month("date_mutation"))
    )

    return df.select(*FINAL_COLUMNS).dropDuplicates()


def run(
    year: int,
    departement: str | None,
    bronze_bucket: str,
    silver_bucket: str
) -> None:
    """
    Run the DVF Bronze -> Silver ETL for the given year/departement.
    Idempotent: overwrites the Silver partition, so re-runnable with the same params
    without duplication.
    """
    spark = build_spark(f"homepedia-silver-dvf-{year}")
    spark.sparkContext.setLogLevel("WARN")

    src_path = _bronze_input(bronze_bucket, year, departement)
    dst_path = build_s3a_uri(silver_bucket, DATASET)
    print(f"[silver-dvf] read  {src_path}")

    raw = read_bronze(spark, src_path)
    raw_count = raw.count()
    silver = transform(raw)
    out_count = silver.count()

    print(f"[silver-dvf] rows raw={raw_count} -> silver={out_count}")
    (
        silver.write.mode("overwrite")
        .partitionBy("year", "code_departement")
        .parquet(dst_path)
    )
    print(f"[silver-dvf] wrote {out_count} rows to {dst_path}")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="DVF Bronze -> Silver ETL")
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
