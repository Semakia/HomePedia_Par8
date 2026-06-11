"""City response schemas (Gold gold.city_metrics + trend)."""

from __future__ import annotations

from pydantic import BaseModel


class CityMetrics(BaseModel):
    code_commune: str
    nom_commune: str
    code_departement: str
    # INSEE enrichment — null until the INSEE pipeline lands.
    region: str | None = None
    population: int | None = None
    revenu_median: float | None = None
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


class CityDetail(CityMetrics):
    trend: list[PriceTrendPoint] = []
