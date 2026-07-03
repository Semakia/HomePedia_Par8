"""Mobility endpoints (Gold mobility.gares) — geolocated train stations.

Served as a point layer the map can toggle on top of the commune choropleth.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_mobility_service
from src.api.schemas.common import Page
from src.api.schemas.mobility import Gare
from src.api.services.mobility_service import MobilityService

router = APIRouter(prefix="/mobility", tags=["mobility"])


@router.get("/gares", response_model=Page[Gare])
def list_gares(
    departement: str | None = Query(None, description="Filter by 2-char dept code"),
    code_commune: str | None = Query(None, description="Filter by commune INSEE code"),
    page: int = Query(1, ge=1),
    size: int = Query(200, ge=1, le=2000),
    service: MobilityService = Depends(get_mobility_service),
) -> Page[Gare]:
    return service.list_gares(departement, code_commune, page, size)
