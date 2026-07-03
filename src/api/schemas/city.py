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
    # --- Affordability (city_metrics) — prix vs revenu, precomputed by the ETL.
    type_commune: str | None = None
    affordability_years: float | None = None  # years of median income for a typical home
    m2_par_an: float | None = None  # m² buyable per year of median income
    affordability_class: str | None = None  # Très abordable | Abordable | Tendu | Très tendu
    # --- Mobility (mobility.commune_transport) — rail access.
    nb_gares: int | None = None
    distance_gare_km: float | None = None
    gare_proche_nom: str | None = None
    desserte_class: str | None = None  # Hub majeur | Bien desservie | Desservie | Non desservie
    # --- Services/amenities (services.commune_equipements) — quality of life.
    niveau_equipement: str | None = None  # Très équipée | Bien équipée | Équipée | Sous-équipée
    nb_total_equipements: int | None = None
    nb_sante: int | None = None
    nb_commerces: int | None = None
    nb_enseignement: int | None = None
    nb_supermarche: int | None = None
    # --- Demographics (demographics.commune_profile) — "is this a young area?".
    pct_moins25: float | None = None
    pct_25_64: float | None = None
    pct_65plus: float | None = None


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
