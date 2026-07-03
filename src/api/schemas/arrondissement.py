"""Arrondissement response schemas (Gold market.arrondissement_metrics).

Intra-city granularity for Paris (75), Lyon (69) and Marseille (13). Same
housing/affordability shape as a commune, plus the parent-commune identity so
the frontend can render a drill-down from a clicked city.
"""

from __future__ import annotations

from pydantic import BaseModel


class ArrondissementMetrics(BaseModel):
    code_arrondissement: str
    year: int | None = None  # DVF vintage (headline = latest year)
    nom_arrondissement: str
    code_commune_parent: str
    nom_commune_parent: str | None = None
    code_departement: str
    region: str | None = None
    population: int | None = None
    insee_ref_year: int | None = None
    revenu_median: float | None = None
    revenu_ref_year: int | None = None
    prix_m2_median: float | None = None
    prix_m2_mean: float | None = None
    surface_median: float | None = None
    nb_transactions: int = 0
    longitude: float | None = None
    latitude: float | None = None
    type_commune: str | None = None
    affordability_years: float | None = None
    m2_par_an: float | None = None
    affordability_class: str | None = None


class ArrondissementYearlyMetric(BaseModel):
    """One DVF vintage of headline metrics for an arrondissement."""

    year: int
    prix_m2_median: float | None = None
    prix_m2_mean: float | None = None
    surface_median: float | None = None
    nb_transactions: int = 0
    affordability_years: float | None = None
    affordability_class: str | None = None


class ArrondissementDetail(ArrondissementMetrics):
    # Inherited fields = latest year headline; this exposes the per-year history.
    # No monthly trend: city_price_trend is keyed by commune, not arrondissement.
    metrics_by_year: list[ArrondissementYearlyMetric] = []
