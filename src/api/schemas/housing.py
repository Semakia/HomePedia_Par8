"""Housing response schemas (Gold gold.housing_price_by_type)."""

from __future__ import annotations

from pydantic import BaseModel


class HousingPriceByType(BaseModel):
    code_commune: str
    type_local: str
    prix_m2_median: float | None = None
    surface_median: float | None = None
    nb_transactions: int = 0
