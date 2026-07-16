"""City endpoints (Gold layer)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from src.api.deps import get_city_service
from src.api.schemas.city import CityDetail, CityMetrics
from src.api.schemas.common import Page
from src.api.services.city_service import CityService

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=Page[CityMetrics])
def list_cities(
    departement: str | None = Query(None, description="Filter by 2-3 char dept code"),
    q: str | None = Query(None, description="Case-insensitive name search"),
    sort: str = Query("prix_m2_median", description="Sort column"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    # Upper bound is generous so the map can pull every commune in one call
    # (France scope ~32k). Normal listing/pagination uses small sizes.
    size: int = Query(50, ge=1, le=40000),
    service: CityService = Depends(get_city_service),
):
    # The full-France map pull is Redis-cached as raw JSON: return it directly
    # so FastAPI doesn't re-validate 32k rows through the response_model (the
    # validation, not the query, is what makes the hit slow).
    if CityService.is_bulk(departement, q, page, size):
        return Response(
            content=service.list_cities_json(sort, order, size),
            media_type="application/json",
        )
    return service.list_cities(departement, q, sort, order, page, size)


@router.get("/{code_commune}", response_model=CityDetail)
def get_city(
    code_commune: str,
    service: CityService = Depends(get_city_service),
) -> CityDetail:
    city = service.get_city(code_commune)
    if city is None:
        raise HTTPException(status_code=404, detail="city not found")
    return city
