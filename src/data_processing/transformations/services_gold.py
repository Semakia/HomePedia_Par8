"""Gold ETL — services (INSEE BPE) serving table into Postgres.

Pivots the BPE Silver (one row per commune × facility type) into one wide row
per commune: counts by domain (A..G), counts of key amenities, and an equipment
level. Paris/Lyon/Marseille arrondissements are rolled up to the parent commune.

Writes via JDBC (truncate + load) to services.commune_equipements.

Run (inside the spark-master container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/services_gold.py
"""

from __future__ import annotations

import os

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark

# BPE domain code -> Gold column. _T (total) is excluded upstream.
DOMAINS = {
    "A": "nb_services", "B": "nb_commerces", "C": "nb_enseignement",
    "D": "nb_sante", "E": "nb_transport", "F": "nb_sport_culture",
    "G": "nb_tourisme",
}
# Key amenities (BPE 2024 nomenclature) -> Gold column.
KEY_TYPES = {
    "nb_medecin": ["D265"],
    "nb_pharmacie": ["D307"],
    "nb_ecole": ["C107", "C108", "C109"],
    "nb_supermarche": ["B104", "B105"],
    "nb_boulangerie": ["B207"],
}


def _jdbc_props() -> tuple[str, dict]:
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "homepedia")
    url = f"jdbc:postgresql://{host}:{port}/{db}"
    props = {
        "user": os.getenv("POSTGRES_USER", "homepedia"),
        "password": os.getenv("POSTGRES_PASSWORD", "homepedia"),
        "driver": "org.postgresql.Driver",
        "stringtype": "unspecified",
    }
    return url, props


def write_gold(df: DataFrame, table: str) -> None:
    url, props = _jdbc_props()
    (
        df.write.format("jdbc")
        .option("url", url)
        .option("dbtable", table)
        .option("truncate", "true")
        .options(**props)
        .mode("overwrite")
        .save()
    )


def rollup_commune(df: DataFrame) -> DataFrame:
    """Map arrondissement INSEE codes to the parent commune (75056/69123/13055)."""
    code = F.col("code_insee")
    parent = (
        F.when(code.startswith("751"), F.lit("75056"))
        .when(code.startswith("6938"), F.lit("69123"))
        .when(code.startswith("132"), F.lit("13055"))
        .otherwise(code)
    )
    return df.withColumn("code_insee", parent)


def niveau_equipement(present_count: Column) -> Column:
    """Equipment level from the number of key amenities present (0-5)."""
    return (
        F.when(present_count == 0, F.lit("Sous-équipée"))
        .when(present_count <= 2, F.lit("Équipée"))
        .when(present_count <= 4, F.lit("Bien équipée"))
        .otherwise(F.lit("Très équipée"))
    )


def build_services(silver: DataFrame) -> DataFrame:
    nb = F.col("nb")
    aggs = [
        F.sum(F.when(F.col("facility_dom") == dom, nb)).alias(col)
        for dom, col in DOMAINS.items()
    ] + [
        F.sum(F.when(F.col("facility_type").isin(codes), nb)).alias(col)
        for col, codes in KEY_TYPES.items()
    ] + [F.max("year").alias("year")]

    agg = silver.groupBy("code_insee").agg(*aggs)

    # nulls (commune without that domain/amenity) -> 0
    for col in list(DOMAINS.values()) + list(KEY_TYPES):
        agg = agg.withColumn(col, F.coalesce(F.col(col), F.lit(0)).cast("int"))

    nb_total = sum((F.col(c) for c in DOMAINS.values()), F.lit(0))
    present = sum(
        (F.when(F.col(c) > 0, 1).otherwise(0) for c in KEY_TYPES), F.lit(0)
    )
    return (
        agg.withColumn("nb_total", nb_total)
        .withColumn("niveau_equipement", niveau_equipement(present))
        .withColumnRenamed("code_insee", "code_commune")
        .select(
            "code_commune", F.col("year").cast("short").alias("year"),
            *DOMAINS.values(), "nb_total", *KEY_TYPES, "niveau_equipement",
        )
    )


def run(silver_bucket: str) -> None:
    spark = build_spark("homepedia-services-to-gold")
    spark.sparkContext.setLogLevel("WARN")

    silver = rollup_commune(spark.read.parquet(build_s3a_uri(silver_bucket, "bpe")))
    services = build_services(silver)

    n = services.count()
    write_gold(services, "services.commune_equipements")
    print(f"[services-gold] communes={n} -> services.commune_equipements")
    spark.stop()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Services (BPE) Silver -> Gold ETL")
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()
    run(args.silver_bucket)


if __name__ == "__main__":
    main()
