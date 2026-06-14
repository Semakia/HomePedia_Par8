"""City response schemas (Gold gold.city_metrics + trend)."""

from __future__ import annotations

from pydantic import BaseModel


class CityMetrics(BaseModel):
    code_commune: str
    year: int | None = None  # DVF vintage (headline = latest year)
    nom_commune: str
    code_departement: str
    # INSEE enrichment — null until the INSEE pipeline lands.
    region: str | None = None
    population: int | None = None
    insee_ref_year: int | None = None  # INSEE population vintage (e.g. 2022)
    revenu_median: float | None = None  # FiLoSoFi median income (€/yr)
    revenu_ref_year: int | None = None  # FiLoSoFi income vintage (e.g. 2023)
    # DVF-derived housing metrics.
    prix_m2_median: float | None = None
    prix_m2_mean: float | None = None
    surface_median: float | None = None
    nb_transactions: int = 0
    longitude: float | None = None
    latitude: float | None = None


class PriceTrendPoint(BaseModel):
    year: int
    month: int
    prix_m2_median: float | None = None
    nb_transactions: int = 0


class YearlyMetric(BaseModel):
    """One DVF vintage of headline metrics for a commune."""

    year: int
    prix_m2_median: float | None = None
    prix_m2_mean: float | None = None
    surface_median: float | None = None
    nb_transactions: int = 0


class CityDetail(CityMetrics):
    # Inherited fields = latest year headline; these expose the history.
    metrics_by_year: list[YearlyMetric] = []
    trend: list[PriceTrendPoint] = []
