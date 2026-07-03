"""Gold ETL — mobility (SNCF) serving tables into Postgres.

Reads the SNCF Silver (one row per station) and writes:
    mobility.gares             · one row per station (map / detail)
    mobility.commune_transport · one row per SERVED commune (count, traffic,
                                 best DRG segment, desserte class)

Writes via JDBC (truncate + load) to the Postgres pointed to by POSTGRES_* env.

Run (inside the spark-master container, repo root on PYTHONPATH):
    spark-submit src/data_processing/transformations/mobility_gold.py
"""

from __future__ import annotations

import os

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from src.data_processing.utils.spark_utils import build_s3a_uri, build_spark

# Beyond this, the nearest station is not meaningful rail access (e.g. DOM
# communes have no SNCF rail -> nearest métropole gare is thousands of km).
DIST_CAP_KM = 150.0


def _haversine_km(
    lat1: Column,
    lon1: Column,
    lat2: Column,
    lon2: Column
) -> Column:
    """
    Haversine great-circle distance in kilometers between two points on the
    Earth specified in decimal degrees (lat/lon).
    See https://en.wikipedia.org/wiki/Haversine_formula

    Args:
        lat1, lon1: first point (decimal degrees)
        lat2, lon2: second point (decimal degrees)
    """
    la1, la2 = F.radians(lat1), F.radians(lat2)
    dlat = la2 - la1
    dlon = F.radians(lon2) - F.radians(lon1)
    a = F.sin(dlat / 2) ** 2 + F.cos(la1) * F.cos(la2) * F.sin(dlon / 2) ** 2
    result = 2 * 6371.0 * F.asin(F.sqrt(a))
    return result


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
    """Map arrondissement INSEE codes to the parent commune.

    SNCF codes Paris/Lyon/Marseille stations by arrondissement (75110, 69383,
    13201...), but the served Gold keys these cities on the parent commune
    (75056/69123/13055). Rolling up lets the city detail find its stations.
    """
    code = F.col("code_commune")
    parent = (
        F.when(code.startswith("751"), F.lit("75056"))
        .when(code.startswith("6938"), F.lit("69123"))
        .when(code.startswith("132"), F.lit("13055"))
        .otherwise(code)
    )
    dataframe = df.withColumn("code_commune", parent)
    return dataframe


def desserte_class(segment: Column) -> Column:
    """SNCF DRG segment -> human desserte class (A < B < C)."""
    return (
        F.when(segment == "A", F.lit("Hub majeur"))
        .when(segment == "B", F.lit("Bien desservie"))
        .when(segment == "C", F.lit("Desservie"))
        .otherwise(F.lit("Desservie"))  # served, segment unknown
    )


def build_gares(silver: DataFrame) -> DataFrame:
    return silver.select(
        "code_uic",
        "nom_gare",
        "code_commune",
        "segment_drg",
        F.col("frequentation").cast("int").alias("frequentation"),
        F.col("frequentation_year").cast("short").alias("frequentation_year"),
        "longitude",
        "latitude",
    )


def build_commune_transport(gares: DataFrame, dvf: DataFrame) -> DataFrame:
    """One row per commune: served (distance 0) + unserved (Non desservie +
    haversine distance to the nearest station, capped at DIST_CAP_KM).

    Commune centroids come from the DVF Silver (avg lat/lon per commune); both
    inputs must already be rolled up to the parent commune.
    """
    served = (
        gares.filter(F.col("code_commune").isNotNull())
        .groupBy("code_commune")
        .agg(
            F.count("*").alias("nb_gares"),
            F.sum("frequentation").cast("long").alias("frequentation_totale"),
            F.max("frequentation_year").cast("short").alias("frequentation_year"),
            F.min("segment_drg").alias("best_segment_drg"),  # A < B < C
        )
        .withColumn("desserte_class", desserte_class(F.col("best_segment_drg")))
        .withColumn("distance_gare_km", F.lit(0.0))
        .withColumn("gare_proche_uic", F.lit(None).cast("string"))
        .withColumn("gare_proche_nom", F.lit(None).cast("string"))
    )

    # Commune centroids (DVF) for the communes that have NO station.
    centroids = (
        dvf.filter(F.col("longitude").isNotNull() & F.col("latitude").isNotNull())
        .groupBy("code_commune")
        .agg(F.avg("longitude").alias("clon"), F.avg("latitude").alias("clat"))
    )
    unserved = centroids.join(
        served.select("code_commune"), on="code_commune", how="left_anti"
    )
    gpts = gares.filter(
        F.col("longitude").isNotNull() & F.col("latitude").isNotNull()
    ).select(
        F.col("code_uic").alias("g_uic"),
        F.col("nom_gare").alias("g_nom"),
        F.col("longitude").alias("glon"),
        F.col("latitude").alias("glat"),
    )
    # Nearest station per unserved commune (broadcast the ~2.8k stations).
    pairs = unserved.crossJoin(F.broadcast(gpts)).withColumn(
        "d",
        _haversine_km(F.col("clat"), F.col("clon"), F.col("glat"), F.col("glon")),
    )
    nearest = pairs.withColumn(
        "rn",
        F.row_number().over(
            Window.partitionBy("code_commune").orderBy(F.col("d").asc())
        ),
    ).filter(F.col("rn") == 1)
    within = F.col("d") <= DIST_CAP_KM  # null out the unreachable (DOM, etc.)
    unserved_rows = nearest.select(
        "code_commune",
        F.lit(0).alias("nb_gares"),
        F.lit(None).cast("long").alias("frequentation_totale"),
        F.lit(None).cast("short").alias("frequentation_year"),
        F.lit(None).cast("string").alias("best_segment_drg"),
        F.lit("Non desservie").alias("desserte_class"),
        F.when(within, F.round("d", 2)).alias("distance_gare_km"),
        F.when(within, F.col("g_uic")).alias("gare_proche_uic"),
        F.when(within, F.col("g_nom")).alias("gare_proche_nom"),
    )
    return served.unionByName(unserved_rows)


def run(silver_bucket: str) -> None:
    spark = build_spark("homepedia-mobility-to-gold")
    spark.sparkContext.setLogLevel("WARN")

    silver = spark.read.parquet(build_s3a_uri(silver_bucket, "sncf_gares"))
    # Roll Paris/Lyon/Marseille arrondissement codes up to the parent commune so
    # the data aligns with market.city_metrics (which is rolled up too).
    silver = rollup_commune(silver)
    # DVF Silver gives commune centroids (avg lat/lon) for the nearest-station
    # distance of unserved communes; roll it up to the same grain.
    dvf = rollup_commune(spark.read.parquet(build_s3a_uri(silver_bucket, "dvf")))
    gares = build_gares(silver)
    commune = build_commune_transport(silver, dvf)

    n_gares = gares.count()
    n_communes = commune.count()
    write_gold(gares, "mobility.gares")
    write_gold(commune, "mobility.commune_transport")

    print(f"[mobility-gold] gares={n_gares} -> mobility.gares")
    print(f"[mobility-gold] served communes={n_communes} -> mobility.commune_transport")
    spark.stop()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Mobility (SNCF) Silver -> Gold ETL")
    parser.add_argument(
        "--silver-bucket", default=os.getenv("S3_SILVER_BUCKET", "homepedia-silver")
    )
    args = parser.parse_args()
    run(args.silver_bucket)


if __name__ == "__main__":
    main()
