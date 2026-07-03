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

from pyspark.sql import Column, DataFrame
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


# Arrondissement (DVF) -> parent commune (INSEE/FiLoSoFi) for the "global city"
# tables. DVF codes Paris/Lyon/Marseille by arrondissement (75101-75120,
# 69381-69389, 13201-13216); we roll them up to 75056/69123/13055 so each city
# is ONE enriched row. The per-arrondissement grain lives in its own table.
def rollup_arrondissements(dvf: DataFrame) -> DataFrame:
    """Rewrite arrondissement code_commune to the parent commune code."""
    code = F.col("code_commune")
    parent = (
        F.when(code.startswith("751"), F.lit("75056"))
        .when(code.startswith("6938"), F.lit("69123"))
        .when(code.startswith("132"), F.lit("13055"))
        .otherwise(code)
    )
    return dvf.withColumn("code_commune", parent)


# Affordability: relative index crossing DVF price and FiLoSoFi income.
# SURFACE_REF = reference dwelling size for the price-to-income ratio.
SURFACE_REF = 70


def affordability_columns(prix: Column, revenu: Column) -> list[Column]:
    """Return [affordability_years, m2_par_an, affordability_class] columns.

    - affordability_years = prix_m2 x SURFACE_REF / revenu (years of median
      income for a reference dwelling; higher = less affordable).
    - m2_par_an = revenu / prix_m2 (m² for one year of income).
    - affordability_class = 4-tier label on affordability_years.
    """
    years = F.when(revenu > 0, F.round(prix * SURFACE_REF / revenu, 1))
    m2 = F.when(prix > 0, F.round(revenu / prix, 1))
    klass = (
        F.when(years.isNull(), F.lit(None))
        .when(years < 7, F.lit("Très abordable"))
        .when(years < 12, F.lit("Abordable"))
        .when(years < 18, F.lit("Tendu"))
        .otherwise(F.lit("Très tendu"))
    )
    return [
        years.alias("affordability_years"),
        m2.alias("m2_par_an"),
        klass.alias("affordability_class"),
    ]


# Commune size class from population. 5 tiers (easy to evolve: edit thresholds).
def commune_type(pop: Column) -> Column:
    return (
        F.when(pop < 2000, F.lit("Village"))
        .when(pop < 5000, F.lit("Bourg"))
        .when(pop < 20000, F.lit("Petite ville"))
        .when(pop < 100000, F.lit("Ville moyenne"))
        .when(pop >= 100000, F.lit("Grande ville"))
        .otherwise(F.lit(None))  # unknown population -> unknown type
    )


def _latest_per_commune(
    df: DataFrame,
    code_col: str
) -> DataFrame:
    """Keep one row per commune = the most recent `year` vintage.
    Args:
        - df : Silver DataFrame (INSEE or FiLoSoFi) with `code_col` and `year`.
        - code_col : column name for the commune code (code_insee).
    Returns:
        - DataFrame with one row per commune = the most recent vintage.
    """
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
    """
        Build city metrics by aggregating DVF, INSEE, and FiLoSoFi data.
        Args:
            dvf : Silver DataFrame with DVF data.
            insee : Silver DataFrame with INSEE data.
            filosofi : Silver DataFrame with FiLoSoFi data.
            regions : Silver DataFrame with region information.
        Returns:
            DataFrame with city metrics.
    """
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
        commune_type(F.col("population")).alias("type_commune"),
        F.col("revenu_median").cast("double").alias("revenu_median"),
        F.col("revenu_ref_year").cast("short").alias("revenu_ref_year"),
        *affordability_columns(
            F.col("prix_m2_median"), F.col("revenu_median")
        ),
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
    """
    Build city price trend by aggregating DVF data.
    Args:
        dvf : Silver DataFrame with DVF data.
    Returns:
        DataFrame with city price trend.
    """
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
    """
    Build housing metrics by type by aggregating DVF data.
    Args:
        dvf : Silver DataFrame with DVF data.
    Returns:
        DataFrame with housing metrics by type.
    """
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


def _is_arrondissement(code: Column) -> Column:
    return (
        code.startswith("751")
        | code.startswith("6938")
        | code.startswith("132")
    )


def build_arrondissement_metrics(
    dvf: DataFrame,
    insee: DataFrame,
    filosofi: DataFrame,
    regions: DataFrame,
) -> DataFrame:
    """Same grain as city_metrics but per municipal arrondissement.

    Built from the NON-rolled DVF (arrondissement codes kept) joined to the
    arrondissements' own ARM-level INSEE/FiLoSoFi figures, with a link back to
    the parent commune (Paris/Lyon/Marseille).
    """
    code = F.col("code_arrondissement")
    parent_code = (
        F.when(code.startswith("751"), F.lit("75056"))
        .when(code.startswith("6938"), F.lit("69123"))
        .when(code.startswith("132"), F.lit("13055"))
    )
    parent_nom = (
        F.when(code.startswith("751"), F.lit("Paris"))
        .when(code.startswith("6938"), F.lit("Lyon"))
        .when(code.startswith("132"), F.lit("Marseille"))
    )

    dvf_agg = (
        dvf.filter(_is_arrondissement(F.col("code_commune")))
        .groupBy("code_commune", "year")
        .agg(
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
        .withColumnRenamed("code_commune", "code_arrondissement")
    )

    insee_sel = _latest_per_commune(insee, "code_insee").select(
        F.col("code_insee").alias("code_arrondissement"),
        F.col("nom_commune").alias("nom_insee"),
        "code_region",
        "population",
        F.col("year").alias("insee_ref_year"),
    )
    filosofi_sel = _latest_per_commune(filosofi, "code_insee").select(
        F.col("code_insee").alias("code_arrondissement"),
        "revenu_median",
        F.col("year").alias("revenu_ref_year"),
    )

    joined = (
        dvf_agg.join(insee_sel, on="code_arrondissement", how="left")
        .join(filosofi_sel, on="code_arrondissement", how="left")
        .join(F.broadcast(regions), on="code_region", how="left")
    )

    return joined.select(
        "code_arrondissement",
        F.col("year").cast("short").alias("year"),
        F.coalesce("nom_insee", "nom_dvf").alias("nom_arrondissement"),
        parent_code.alias("code_commune_parent"),
        parent_nom.alias("nom_commune_parent"),
        "code_departement",
        F.col("region_name").alias("region"),
        F.col("population").cast("int").alias("population"),
        F.col("insee_ref_year").cast("short").alias("insee_ref_year"),
        commune_type(F.col("population")).alias("type_commune"),
        F.col("revenu_median").cast("double").alias("revenu_median"),
        F.col("revenu_ref_year").cast("short").alias("revenu_ref_year"),
        *affordability_columns(
            F.col("prix_m2_median"), F.col("revenu_median")
        ),
        F.round("prix_m2_median", 2).alias("prix_m2_median"),
        "prix_m2_mean",
        F.round("surface_median", 2).alias("surface_median"),
        "nb_transactions",
        "longitude",
        "latitude",
        "period_start",
        "period_end",
    )


def build_demographics(demo: DataFrame) -> DataFrame:
    """Wide age/sex profile per commune (commune grain, arrondissements excluded).

    From the long Silver (commune x year x sex x disjoint age band), compute the
    headline shares used for segmentation: % under 25 / 25-64 / 65+ and % women.
    """
    young = ["Y_LT15", "Y15T24"]
    mid = ["Y25T39", "Y40T54", "Y55T64"]
    old = ["Y65T79", "Y_GE80"]
    is_total = F.col("sex") == "_T"
    pop = F.col("population")

    agg = (
        demo.filter(~_is_arrondissement(F.col("code_insee")))
        .groupBy("code_insee", "year")
        .agg(
            F.sum(F.when(is_total, pop).otherwise(0)).alias("total"),
            F.sum(F.when(is_total & F.col("age_band").isin(young), pop).otherwise(0)).alias("young"),
            F.sum(F.when(is_total & F.col("age_band").isin(mid), pop).otherwise(0)).alias("mid"),
            F.sum(F.when(is_total & F.col("age_band").isin(old), pop).otherwise(0)).alias("old"),
            F.sum(F.when(F.col("sex") == "F", pop).otherwise(0)).alias("femmes"),
        )
        .filter(F.col("total") > 0)
    )
    total = F.col("total")
    return agg.select(
        F.col("code_insee").alias("code_commune"),
        F.col("year").cast("short").alias("year"),
        total.cast("int").alias("population_total"),
        F.round(F.col("young") / total * 100, 2).alias("pct_moins25"),
        F.round(F.col("mid") / total * 100, 2).alias("pct_25_64"),
        F.round(F.col("old") / total * 100, 2).alias("pct_65plus"),
        F.round(F.col("femmes") / total * 100, 2).alias("part_femmes"),
    )


def run(silver_bucket: str) -> None:
    """
    Run the Silver -> Gold ETL.
    Args:
        silver_bucket : S3 bucket name where Silver Parquet files are stored.
    """
    spark = build_spark("homepedia-silver-to-gold")
    spark.sparkContext.setLogLevel("WARN")

    dvf_raw = spark.read.parquet(build_s3a_uri(silver_bucket, "dvf"))
    # Global-city grain: roll Paris/Lyon/Marseille arrondissements up to their
    # parent commune so each city is one enriched row. The per-arrondissement
    # grain (market.arrondissement_metrics) uses the NON-rolled dvf_raw.
    dvf = rollup_arrondissements(dvf_raw)
    insee = spark.read.parquet(build_s3a_uri(silver_bucket, "insee"))
    filosofi = spark.read.parquet(build_s3a_uri(silver_bucket, "filosofi"))
    demo = spark.read.parquet(build_s3a_uri(silver_bucket, "insee_demographics"))
    regions = spark.createDataFrame(
        list(REGIONS.items()), ["code_region", "region_name"]
    )

    city_metrics = build_city_metrics(dvf, insee, filosofi, regions)
    trend = build_price_trend(dvf)
    by_type = build_housing_by_type(dvf)
    arr_metrics = build_arrondissement_metrics(dvf_raw, insee, filosofi, regions)
    demographics = build_demographics(demo)

    n_cities = city_metrics.count()
    n_arr = arr_metrics.count()
    n_demo = demographics.count()
    write_gold(city_metrics, "market.city_metrics")
    write_gold(arr_metrics, "market.arrondissement_metrics")
    write_gold(trend, "market.city_price_trend")
    write_gold(by_type, "market.housing_price_by_type")
    write_gold(demographics, "demographics.commune_profile")

    print(f"[silver-to-gold] city_metrics={n_cities} -> market.city_metrics")
    print(f"[silver-to-gold] arrondissement_metrics={n_arr} rows")
    print(f"[silver-to-gold] demographics={n_demo} -> demographics.commune_profile")
    print("[silver-to-gold] also wrote city_price_trend, housing_price_by_type")
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
