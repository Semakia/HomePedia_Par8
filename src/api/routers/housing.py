"""Housing endpoints (Gold layer) — per-type price metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_housing_service
from src.api.schemas.common import Page
from src.api.schemas.housing import HousingPriceByType
from src.api.services.housing_service import HousingService

router = APIRouter(prefix="/housing", tags=["housing"])


@router.get("/prices", response_model=Page[HousingPriceByType])
def list_prices(
    code_commune: str | None = Query(None),
    type_local: str | None = Query(None, description="Maison | Appartement"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    service: HousingService = Depends(get_housing_service),
) -> Page[HousingPriceByType]:
    return service.list_prices(code_commune, type_local, page, size)
