"""Gold ETL — build the serving tables from Silver (DVF x INSEE) into Postgres.

Reads DVF Silver (housing transactions) and INSEE Silver (commune population),
pre-aggregates per commune, enriches with INSEE (population, region name), and
writes the three Gold tables consumed by the API:
    gold.city_metrics · gold.city_price_trend · gold.housing_price_by_type

Writes via JDBC (truncate + load) to the Postgres pointed to by POSTGRES_* env.
INSEE columns are left nullable for communes absent from the INSEE referential.

Run (inside the spark-master container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/silver_to_gold.py
"""

from __future__ import annotations

import os

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark

# INSEE region code -> human-readable name (the API/frontend wants the label).
REGIONS = {
    "11": "Île-de-France", "24": "Centre-Val de Loire",
    "27": "Bourgogne-Franche-Comté", "28": "Normandie", "32": "Hauts-de-France",
    "44": "Grand Est", "52": "Pays de la Loire", "53": "Bretagne",
    "75": "Nouvelle-Aquitaine", "76": "Occitanie", "84": "Auvergne-Rhône-Alpes",
    "93": "Provence-Alpes-Côte d'Azur", "94": "Corse",
    "01": "Guadeloupe", "02": "Martinique", "03": "Guyane",
    "04": "La Réunion", "06": "Mayotte",
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
        # let Postgres coerce strings into varchar/text without explicit casts
        "stringtype": "unspecified",
    }
    return url, props


def write_gold(df: DataFrame, table: str) -> None:
    url, props = _jdbc_props()
    (
        df.write.format("jdbc")
        .option("url", url)
        .option("dbtable", table)
        .option("truncate", "true")  # keep table definition + indexes, replace rows
        .options(**props)
        .mode("overwrite")
        .save()
    )


def _latest_per_commune(df: DataFrame, code_col: str) -> DataFrame:
    """Keep one row per commune = the most recent `year` vintage."""
    return (
        df.withColumn(
            "_rn",
            F.row_number().over(
                Window.partitionBy(code_col).orderBy(F.col("year").desc())
            ),
        )
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


def build_city_metrics(
    dvf: DataFrame,
    insee: DataFrame,
    filosofi: DataFrame,
    regions: DataFrame,
) -> DataFrame:
    # One row per commune AND per DVF year -> each vintage keeps its own median
    # (no cross-year price mixing). The API picks the latest year as headline.
    dvf_agg = dvf.groupBy("code_commune", "year").agg(
        F.first("nom_commune", ignorenulls=True).alias("nom_dvf"),
        F.first("code_departement", ignorenulls=True).alias("code_departement"),
        F.expr("percentile_approx(prix_m2, 0.5)").alias("prix_m2_median"),
        F.round(F.avg("prix_m2"), 2).alias("prix_m2_mean"),
        F.expr("percentile_approx(surface_reelle_bati, 0.5)").alias("surface_median"),
        F.count("*").alias("nb_transactions"),
        F.round(F.avg("longitude"), 6).alias("longitude"),
        F.round(F.avg("latitude"), 6).alias("latitude"),
        F.min("date_mutation").alias("period_start"),
        F.max("date_mutation").alias("period_end"),
    )

    # INSEE/FiLoSoFi Silver can carry several vintages (year column). Keep one
    # row per commune = the most recent vintage, surfacing each ref year.
    insee_sel = _latest_per_commune(insee, "code_insee").select(
        F.col("code_insee").alias("code_commune"),
        F.col("nom_commune").alias("nom_insee"),
        "code_region",
        "population",
        F.col("year").alias("insee_ref_year"),
    )

    filosofi_sel = _latest_per_commune(filosofi, "code_insee").select(
        F.col("code_insee").alias("code_commune"),
        "revenu_median",
        F.col("year").alias("revenu_ref_year"),
    )

    joined = (
        dvf_agg.join(insee_sel, on="code_commune", how="left")
        .join(filosofi_sel, on="code_commune", how="left")
        .join(F.broadcast(regions), on="code_region", how="left")
    )

    return joined.select(
        "code_commune",
        F.col("year").cast("short").alias("year"),
        F.coalesce("nom_insee", "nom_dvf").alias("nom_commune"),
        "code_departement",
        F.col("region_name").alias("region"),
        F.col("population").cast("int").alias("population"),
        F.col("insee_ref_year").cast("short").alias("insee_ref_year"),
        F.col("revenu_median").cast("double").alias("revenu_median"),
        F.col("revenu_ref_year").cast("short").alias("revenu_ref_year"),
        F.round("prix_m2_median", 2).alias("prix_m2_median"),
        "prix_m2_mean",
        F.round("surface_median", 2).alias("surface_median"),
        "nb_transactions",
        "longitude",
        "latitude",
        "period_start",
        "period_end",
    )


def build_price_trend(dvf: DataFrame) -> DataFrame:
    return (
        dvf.groupBy("code_commune", "year", "month")
        .agg(
            F.expr("percentile_approx(prix_m2, 0.5)").alias("prix_m2_median"),
            F.count("*").alias("nb_transactions"),
        )
        .select(
            "code_commune",
            F.col("year").cast("short").alias("year"),
            F.col("month").cast("short").alias("month"),
            F.round("prix_m2_median", 2).alias("prix_m2_median"),
            "nb_transactions",
        )
    )


def build_housing_by_type(dvf: DataFrame) -> DataFrame:
    return (
        dvf.groupBy("code_commune", "type_local")
        .agg(
            F.expr("percentile_approx(prix_m2, 0.5)").alias("prix_m2_median"),
            F.expr("percentile_approx(surface_reelle_bati, 0.5)").alias("surface_median"),
            F.count("*").alias("nb_transactions"),
        )
        .select(
            "code_commune",
            "type_local",
            F.round("prix_m2_median", 2).alias("prix_m2_median"),
            F.round("surface_median", 2).alias("surface_median"),
            "nb_transactions",
        )
    )


def run(silver_bucket: str) -> None:
    spark = build_spark("homepedia-silver-to-gold")
    spark.sparkContext.setLogLevel("WARN")

    dvf = spark.read.parquet(build_s3a_uri(silver_bucket, "dvf"))
    insee = spark.read.parquet(build_s3a_uri(silver_bucket, "insee"))
    filosofi = spark.read.parquet(build_s3a_uri(silver_bucket, "filosofi"))
    regions = spark.createDataFrame(
        list(REGIONS.items()), ["code_region", "region_name"]
    )

    city_metrics = build_city_metrics(dvf, insee, filosofi, regions)
    trend = build_price_trend(dvf)
    by_type = build_housing_by_type(dvf)

    n_cities = city_metrics.count()
    write_gold(city_metrics, "gold.city_metrics")
    write_gold(trend, "gold.city_price_trend")
    write_gold(by_type, "gold.housing_price_by_type")

    print(f"[silver-to-gold] city_metrics={n_cities} rows -> gold.city_metrics")
    print("[silver-to-gold] also wrote gold.city_price_trend, gold.housing_price_by_type")
    spark.stop()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Silver -> Gold ETL (Postgres)")
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()
    run(args.silver_bucket)


if __name__ == "__main__":
    main()
