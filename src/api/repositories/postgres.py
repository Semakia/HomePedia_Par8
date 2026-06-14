"""PostgreSQL implementations of the Gold repositories (SQLAlchemy Core).

Queries the `gold.*` tables. They are empty until silver_to_gold runs, so every
method returns well-formed-but-empty results today — the API contract holds.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.api.repositories.base import CityRepository, HousingRepository
from src.api.schemas.city import (
    CityDetail,
    CityMetrics,
    PriceTrendPoint,
    YearlyMetric,
)
from src.api.schemas.housing import HousingPriceByType

# Whitelist sortable columns to keep ORDER BY injection-safe.
_CITY_SORTS = {
    "prix_m2_median": "prix_m2_median",
    "nb_transactions": "nb_transactions",
    "population": "population",
    "nom_commune": "nom_commune",
}
_CITY_COLUMNS = (
    "code_commune, year, nom_commune, code_departement, region, "
    "population, insee_ref_year, revenu_median, revenu_ref_year, "
    "prix_m2_median, prix_m2_mean, surface_median, nb_transactions, "
    "longitude, latitude"
)


class PostgresCityRepository(CityRepository):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

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
        # Headline = latest year per commune (DISTINCT ON), then sort the
        # one-row-per-city set. NULLS LAST so populated rows surface first.
        latest = (
            f"SELECT DISTINCT ON (code_commune) {_CITY_COLUMNS} "
            f"FROM gold.city_metrics {where} "
            "ORDER BY code_commune, year DESC"
        )
        list_sql = text(
            f"SELECT * FROM ({latest}) latest "
            f"ORDER BY {sort_col} {direction} NULLS LAST, code_commune "
            "LIMIT :limit OFFSET :offset"
        )
        count_sql = text(
            f"SELECT count(*) FROM (SELECT DISTINCT ON (code_commune) "
            f"code_commune FROM gold.city_metrics {where}) latest"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(list_sql, params).mappings().all()
            total = conn.execute(count_sql, params).scalar_one()
        return [CityMetrics(**dict(r)) for r in rows], int(total)

    def get_city(self, code_commune: str) -> CityDetail | None:
        with self.engine.connect() as conn:
            # Headline = most recent year for this commune.
            row = conn.execute(
                text(f"SELECT DISTINCT ON (code_commune) {_CITY_COLUMNS} "
                     "FROM gold.city_metrics WHERE code_commune = :c "
                     "ORDER BY code_commune, year DESC"),
                {"c": code_commune},
            ).mappings().first()
            if row is None:
                return None
            # Per-year headline history (richest first year -> latest).
            by_year = conn.execute(
                text("SELECT year, prix_m2_median, prix_m2_mean, "
                     "surface_median, nb_transactions FROM gold.city_metrics "
                     "WHERE code_commune = :c ORDER BY year"),
                {"c": code_commune},
            ).mappings().all()
            # Monthly price trend (chart granularity).
            trend = conn.execute(
                text("SELECT year, month, prix_m2_median, nb_transactions "
                     "FROM gold.city_price_trend WHERE code_commune = :c "
                     "ORDER BY year, month"),
                {"c": code_commune},
            ).mappings().all()
        return CityDetail(
            **dict(row),
            metrics_by_year=[YearlyMetric(**dict(m)) for m in by_year],
            trend=[PriceTrendPoint(**dict(t)) for t in trend],
        )


class PostgresHousingRepository(HousingRepository):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_prices(self, code_commune, type_local, offset, limit):
        where = (
            "WHERE (:c IS NULL OR code_commune = :c) "
            "AND (:t IS NULL OR type_local = :t)"
        )
        params = {"c": code_commune, "t": type_local, "limit": limit, "offset": offset}
        list_sql = text(
            "SELECT code_commune, type_local, prix_m2_median, surface_median, "
            f"nb_transactions FROM gold.housing_price_by_type {where} "
            "ORDER BY code_commune, type_local LIMIT :limit OFFSET :offset"
        )
        count_sql = text(f"SELECT count(*) FROM gold.housing_price_by_type {where}")
        with self.engine.connect() as conn:
            rows = conn.execute(list_sql, params).mappings().all()
            total = conn.execute(count_sql, params).scalar_one()
        return [HousingPriceByType(**dict(r)) for r in rows], int(total)
