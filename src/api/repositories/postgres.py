"""PostgreSQL implementations of the Gold repositories (SQLAlchemy Core).

Queries the Gold tables under the configured schema (``settings.gold_schema``,
default ``gold``; the remote dev DB namespaces them under ``market``). The
schema is validated as a bare identifier at config load, so interpolating it
into SQL stays injection-safe.

The commune endpoints enrich ``city_metrics`` with the sibling Gold pipelines —
demographics, rail mobility and amenities — which live in their own fixed
schemas (``demographics`` / ``mobility`` / ``services``), not under the
``gold_schema`` namespace. They are LEFT-joined so a commune missing from any of
them still returns its housing row (the extra fields come back null).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.api.repositories.base import (
    ArrondissementRepository,
    CityRepository,
    HousingRepository,
    MobilityRepository,
)
from src.api.schemas.arrondissement import (
    ArrondissementDetail,
    ArrondissementMetrics,
    ArrondissementYearlyMetric,
)
from src.api.schemas.city import (
    CityDetail,
    CityMetrics,
    PriceTrendPoint,
    YearlyMetric,
)
from src.api.schemas.housing import HousingPriceByType
from src.api.schemas.mobility import Gare

# Sibling Gold schemas (fixed names on the data platform; the gold_schema
# rename to "market" only applies to the housing/market tables).
DEMOGRAPHICS_SCHEMA = "demographics"
MOBILITY_SCHEMA = "mobility"
SERVICES_SCHEMA = "services"

# Whitelist sortable columns to keep ORDER BY injection-safe. Values are output
# column names of the enriched SELECT (so joined columns can be sorted too).
_CITY_SORTS = {
    "prix_m2_median": "prix_m2_median",
    "nb_transactions": "nb_transactions",
    "population": "population",
    "nom_commune": "nom_commune",
    "affordability_years": "affordability_years",
    "revenu_median": "revenu_median",
    "distance_gare_km": "distance_gare_km",
    "pct_moins25": "pct_moins25",
}
# Columns read straight from city_metrics (qualified to the latest-year row).
_CM_COLS = (
    "code_commune, year, nom_commune, code_departement, region, "
    "population, insee_ref_year, revenu_median, revenu_ref_year, "
    "prix_m2_median, prix_m2_mean, surface_median, nb_transactions, "
    "longitude, latitude, type_commune, affordability_years, m2_par_an, "
    "affordability_class"
)


def _enriched_city_select(schema: str, where: str) -> str:
    """One row per commune (latest DVF year) joined to its sibling-pipeline
    profiles (rail / amenities / demographics), each reduced to its own latest
    vintage. Returns SQL with a single `{where}` already inlined."""
    return f"""
    WITH latest_city AS (
        SELECT DISTINCT ON (code_commune) {_CM_COLS}
        FROM {schema}.city_metrics {where}
        ORDER BY code_commune, year DESC
    ),
    latest_demo AS (
        SELECT DISTINCT ON (code_commune)
            code_commune, pct_moins25, pct_25_64, pct_65plus
        FROM {DEMOGRAPHICS_SCHEMA}.commune_profile
        ORDER BY code_commune, year DESC
    ),
    latest_equip AS (
        SELECT DISTINCT ON (code_commune)
            code_commune, niveau_equipement, nb_total, nb_sante,
            nb_commerces, nb_enseignement, nb_supermarche
        FROM {SERVICES_SCHEMA}.commune_equipements
        ORDER BY code_commune, year DESC
    )
    SELECT lc.*,
        t.nb_gares, t.distance_gare_km, t.gare_proche_nom, t.desserte_class,
        e.niveau_equipement,
        e.nb_total AS nb_total_equipements,
        e.nb_sante, e.nb_commerces, e.nb_enseignement, e.nb_supermarche,
        d.pct_moins25, d.pct_25_64, d.pct_65plus
    FROM latest_city lc
    LEFT JOIN {MOBILITY_SCHEMA}.commune_transport t
        ON t.code_commune = lc.code_commune
    LEFT JOIN latest_equip e ON e.code_commune = lc.code_commune
    LEFT JOIN latest_demo d ON d.code_commune = lc.code_commune
    """


class PostgresCityRepository(CityRepository):
    def __init__(self, engine: Engine, schema: str = "gold") -> None:
        self.engine = engine
        self.schema = schema

    def list_cities(self, departement, query, sort, order, offset, limit):
        sort_col = _CITY_SORTS.get(sort, "prix_m2_median")
        direction = "ASC" if order.lower() == "asc" else "DESC"
        where = (
            "WHERE (:dept IS NULL OR code_departement = :dept) "
            "AND (:q IS NULL OR lower(nom_commune) LIKE :q)"
        )
        params = {
            "dept": departement,
            "q": f"%{query.lower()}%" if query else None,
            "limit": limit,
            "offset": offset,
        }
        # Enriched, one row per commune (latest year), then sort the set.
        # NULLS LAST so populated rows surface first.
        list_sql = text(
            f"SELECT * FROM ({_enriched_city_select(self.schema, where)}) enriched "
            f"ORDER BY {sort_col} {direction} NULLS LAST, code_commune "
            "LIMIT :limit OFFSET :offset"
        )
        count_sql = text(
            f"SELECT count(*) FROM (SELECT DISTINCT ON (code_commune) "
            f"code_commune FROM {self.schema}.city_metrics {where}) latest"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(list_sql, params).mappings().all()
            total = conn.execute(count_sql, params).scalar_one()
        return [CityMetrics(**dict(r)) for r in rows], int(total)

    def get_city(self, code_commune: str) -> CityDetail | None:
        where = "WHERE code_commune = :c"
        with self.engine.connect() as conn:
            # Headline = most recent year for this commune, fully enriched.
            row = conn.execute(
                text(_enriched_city_select(self.schema, where)),
                {"c": code_commune},
            ).mappings().first()
            if row is None:
                return None
            # Per-year headline history (oldest -> latest).
            by_year = conn.execute(
                text("SELECT year, prix_m2_median, prix_m2_mean, "
                     f"surface_median, nb_transactions FROM {self.schema}.city_metrics "
                     "WHERE code_commune = :c ORDER BY year"),
                {"c": code_commune},
            ).mappings().all()
            # Monthly price trend (chart granularity).
            trend = conn.execute(
                text("SELECT year, month, prix_m2_median, nb_transactions "
                     f"FROM {self.schema}.city_price_trend WHERE code_commune = :c "
                     "ORDER BY year, month"),
                {"c": code_commune},
            ).mappings().all()
        return CityDetail(
            **dict(row),
            metrics_by_year=[YearlyMetric(**dict(m)) for m in by_year],
            trend=[PriceTrendPoint(**dict(t)) for t in trend],
        )

    def get_national(self) -> CityDetail:
        # Enriched per-commune set (latest year, joined to sibling pipelines),
        # reused as a CTE so the headline aggregate and the modal-class picks
        # share one scan. Quantities = exact SUM; prices/income/demographics =
        # transaction/population-weighted means over every commune.
        enriched = _enriched_city_select(self.schema, "")
        headline_sql = text(f"""
        WITH enriched AS (
            {enriched}
        )
        SELECT
            'FR' AS code_commune,
            max(year) AS year,
            'France entière' AS nom_commune,
            'FR' AS code_departement,
            NULL AS region,
            sum(population) AS population,
            max(insee_ref_year) AS insee_ref_year,
            round((sum(revenu_median * population)
                / nullif(sum(population), 0))::numeric, 0) AS revenu_median,
            max(revenu_ref_year) AS revenu_ref_year,
            round((sum(prix_m2_median * nb_transactions)
                / nullif(sum(nb_transactions), 0))::numeric, 1)
                AS prix_m2_median,
            round((sum(prix_m2_mean * nb_transactions)
                / nullif(sum(nb_transactions), 0))::numeric, 1)
                AS prix_m2_mean,
            round((sum(surface_median * nb_transactions)
                / nullif(sum(nb_transactions), 0))::numeric, 1)
                AS surface_median,
            sum(nb_transactions) AS nb_transactions,
            NULL AS longitude, NULL AS latitude, NULL AS type_commune,
            round((sum(affordability_years * population)
                / nullif(sum(population), 0))::numeric, 1)
                AS affordability_years,
            round((sum(m2_par_an * population)
                / nullif(sum(population), 0))::numeric, 1) AS m2_par_an,
            (SELECT affordability_class FROM enriched
                 WHERE affordability_class IS NOT NULL
                 GROUP BY affordability_class
                 ORDER BY sum(nb_transactions) DESC LIMIT 1)
                AS affordability_class,
            sum(nb_gares) AS nb_gares,
            NULL AS distance_gare_km, NULL AS gare_proche_nom,
            (SELECT desserte_class FROM enriched
                 WHERE desserte_class IS NOT NULL
                 GROUP BY desserte_class
                 ORDER BY sum(nb_transactions) DESC LIMIT 1)
                AS desserte_class,
            (SELECT niveau_equipement FROM enriched
                 WHERE niveau_equipement IS NOT NULL
                 GROUP BY niveau_equipement
                 ORDER BY sum(nb_transactions) DESC LIMIT 1)
                AS niveau_equipement,
            sum(nb_total_equipements) AS nb_total_equipements,
            sum(nb_sante) AS nb_sante,
            sum(nb_commerces) AS nb_commerces,
            sum(nb_enseignement) AS nb_enseignement,
            sum(nb_supermarche) AS nb_supermarche,
            round((sum(pct_moins25 * population)
                / nullif(sum(population), 0))::numeric, 1) AS pct_moins25,
            round((sum(pct_25_64 * population)
                / nullif(sum(population), 0))::numeric, 1) AS pct_25_64,
            round((sum(pct_65plus * population)
                / nullif(sum(population), 0))::numeric, 1) AS pct_65plus
        FROM enriched
        """)
        # Per-year national headline: prices weighted by volume, txns summed.
        by_year_sql = text(f"""
            SELECT year,
                round((sum(prix_m2_median * nb_transactions)
                    / nullif(sum(nb_transactions), 0))::numeric, 1)
                    AS prix_m2_median,
                round((sum(prix_m2_mean * nb_transactions)
                    / nullif(sum(nb_transactions), 0))::numeric, 1)
                    AS prix_m2_mean,
                round((sum(surface_median * nb_transactions)
                    / nullif(sum(nb_transactions), 0))::numeric, 1)
                    AS surface_median,
                sum(nb_transactions) AS nb_transactions
            FROM {self.schema}.city_metrics
            WHERE year IS NOT NULL
            GROUP BY year ORDER BY year
        """)
        # National monthly trend: same volume-weighted median-of-medians.
        trend_sql = text(f"""
            SELECT year, month,
                round((sum(prix_m2_median * nb_transactions)
                    / nullif(sum(nb_transactions), 0))::numeric, 1)
                    AS prix_m2_median,
                sum(nb_transactions) AS nb_transactions
            FROM {self.schema}.city_price_trend
            GROUP BY year, month ORDER BY year, month
        """)
        with self.engine.connect() as conn:
            row = conn.execute(headline_sql).mappings().first()
            by_year = conn.execute(by_year_sql).mappings().all()
            trend = conn.execute(trend_sql).mappings().all()
        return CityDetail(
            **dict(row),
            metrics_by_year=[YearlyMetric(**dict(m)) for m in by_year],
            trend=[PriceTrendPoint(**dict(t)) for t in trend],
        )


class PostgresHousingRepository(HousingRepository):
    def __init__(self, engine: Engine, schema: str = "gold") -> None:
        self.engine = engine
        self.schema = schema

    def list_prices(self, code_commune, type_local, offset, limit):
        where = (
            "WHERE (:c IS NULL OR code_commune = :c) "
            "AND (:t IS NULL OR type_local = :t)"
        )
        params = {"c": code_commune, "t": type_local, "limit": limit, "offset": offset}
        list_sql = text(
            "SELECT code_commune, type_local, prix_m2_median, surface_median, "
            f"nb_transactions FROM {self.schema}.housing_price_by_type {where} "
            "ORDER BY code_commune, type_local LIMIT :limit OFFSET :offset"
        )
        count_sql = text(
            f"SELECT count(*) FROM {self.schema}.housing_price_by_type {where}"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(list_sql, params).mappings().all()
            total = conn.execute(count_sql, params).scalar_one()
        return [HousingPriceByType(**dict(r)) for r in rows], int(total)

    def list_prices_national(self) -> list[HousingPriceByType]:
        # One row per dwelling type, prices volume-weighted, txns summed.
        sql = text(
            "SELECT 'FR' AS code_commune, type_local, "
            "round((sum(prix_m2_median * nb_transactions) "
            "/ nullif(sum(nb_transactions), 0))::numeric, 1) AS prix_m2_median, "
            "round((sum(surface_median * nb_transactions) "
            "/ nullif(sum(nb_transactions), 0))::numeric, 1) AS surface_median, "
            "sum(nb_transactions) AS nb_transactions "
            f"FROM {self.schema}.housing_price_by_type "
            "GROUP BY type_local ORDER BY type_local"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(sql).mappings().all()
        return [HousingPriceByType(**dict(r)) for r in rows]


# Arrondissement headline columns (market.arrondissement_metrics).
_ARR_COLS = (
    "code_arrondissement, year, nom_arrondissement, code_commune_parent, "
    "nom_commune_parent, code_departement, region, population, insee_ref_year, "
    "revenu_median, revenu_ref_year, prix_m2_median, prix_m2_mean, "
    "surface_median, nb_transactions, longitude, latitude, type_commune, "
    "affordability_years, m2_par_an, affordability_class"
)
_ARR_SORTS = {
    "prix_m2_median": "prix_m2_median",
    "nb_transactions": "nb_transactions",
    "population": "population",
    "nom_arrondissement": "nom_arrondissement",
    "affordability_years": "affordability_years",
    "revenu_median": "revenu_median",
}


class PostgresArrondissementRepository(ArrondissementRepository):
    def __init__(self, engine: Engine, schema: str = "gold") -> None:
        self.engine = engine
        self.schema = schema

    def list_arrondissements(
        self, departement, code_commune_parent, sort, order, offset, limit
    ):
        sort_col = _ARR_SORTS.get(sort, "code_arrondissement")
        direction = "ASC" if order.lower() == "asc" else "DESC"
        where = (
            "WHERE (:dept IS NULL OR code_departement = :dept) "
            "AND (:parent IS NULL OR code_commune_parent = :parent)"
        )
        params = {
            "dept": departement,
            "parent": code_commune_parent,
            "limit": limit,
            "offset": offset,
        }
        latest = (
            f"SELECT DISTINCT ON (code_arrondissement) {_ARR_COLS} "
            f"FROM {self.schema}.arrondissement_metrics {where} "
            "ORDER BY code_arrondissement, year DESC"
        )
        list_sql = text(
            f"SELECT * FROM ({latest}) latest "
            f"ORDER BY {sort_col} {direction} NULLS LAST, code_arrondissement "
            "LIMIT :limit OFFSET :offset"
        )
        count_sql = text(
            f"SELECT count(*) FROM (SELECT DISTINCT ON (code_arrondissement) "
            f"code_arrondissement FROM {self.schema}.arrondissement_metrics {where}) l"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(list_sql, params).mappings().all()
            total = conn.execute(count_sql, params).scalar_one()
        return [ArrondissementMetrics(**dict(r)) for r in rows], int(total)

    def get_arrondissement(self, code: str) -> ArrondissementDetail | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT DISTINCT ON (code_arrondissement) {_ARR_COLS} "
                     f"FROM {self.schema}.arrondissement_metrics "
                     "WHERE code_arrondissement = :c "
                     "ORDER BY code_arrondissement, year DESC"),
                {"c": code},
            ).mappings().first()
            if row is None:
                return None
            by_year = conn.execute(
                text("SELECT year, prix_m2_median, prix_m2_mean, surface_median, "
                     "nb_transactions, affordability_years, affordability_class "
                     f"FROM {self.schema}.arrondissement_metrics "
                     "WHERE code_arrondissement = :c ORDER BY year"),
                {"c": code},
            ).mappings().all()
        return ArrondissementDetail(
            **dict(row),
            metrics_by_year=[ArrondissementYearlyMetric(**dict(m)) for m in by_year],
        )


class PostgresMobilityRepository(MobilityRepository):
    """Gares live in a fixed `mobility` schema, independent of gold_schema."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_gares(self, departement, code_commune, offset, limit):
        where = (
            "WHERE (:dept IS NULL OR left(code_commune, 2) = :dept) "
            "AND (:c IS NULL OR code_commune = :c) "
            "AND latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        params = {"dept": departement, "c": code_commune, "limit": limit, "offset": offset}
        list_sql = text(
            "SELECT code_uic, nom_gare, code_commune, segment_drg, frequentation, "
            f"frequentation_year, longitude, latitude FROM {MOBILITY_SCHEMA}.gares {where} "
            "ORDER BY frequentation DESC NULLS LAST, code_uic LIMIT :limit OFFSET :offset"
        )
        count_sql = text(f"SELECT count(*) FROM {MOBILITY_SCHEMA}.gares {where}")
        with self.engine.connect() as conn:
            rows = conn.execute(list_sql, params).mappings().all()
            total = conn.execute(count_sql, params).scalar_one()
        return [Gare(**dict(r)) for r in rows], int(total)
