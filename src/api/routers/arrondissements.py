"""Arrondissement endpoints (Gold market.arrondissement_metrics).

Intra-city granularity for Paris (75), Lyon (69) and Marseille (13) — powers the
drill-down opened when the user clicks one of those communes on the map.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_arrondissement_service
from src.api.schemas.arrondissement import ArrondissementDetail, ArrondissementMetrics
from src.api.schemas.common import Page
from src.api.services.arrondissement_service import ArrondissementService

router = APIRouter(prefix="/arrondissements", tags=["arrondissements"])


@router.get("", response_model=Page[ArrondissementMetrics])
def list_arrondissements(
    departement: str | None = Query(None, description="Filter by dept (75 | 69 | 13)"),
    code_commune_parent: str | None = Query(
        None, description="Filter by parent commune INSEE code (e.g. 75056)"
    ),
    sort: str = Query("code_arrondissement", description="Sort column"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    service: ArrondissementService = Depends(get_arrondissement_service),
) -> Page[ArrondissementMetrics]:
    return service.list_arrondissements(
        departement, code_commune_parent, sort, order, page, size
    )


@router.get("/{code_arrondissement}", response_model=ArrondissementDetail)
def get_arrondissement(
    code_arrondissement: str,
    service: ArrondissementService = Depends(get_arrondissement_service),
) -> ArrondissementDetail:
    arr = service.get_arrondissement(code_arrondissement)
    if arr is None:
        raise HTTPException(status_code=404, detail="arrondissement not found")
    return arr
