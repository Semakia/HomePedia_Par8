"""National ("France entière") endpoints (Gold layer, aggregated).

France-wide aggregate shaped exactly like a city so the frontend reuses the
per-city stats page unchanged. See NationalService for the weighting caveats.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from src.api.deps import get_national_service
from src.api.schemas.city import CityDetail
from src.api.schemas.common import Page
from src.api.schemas.housing import HousingPriceByType
from src.api.services.national_service import NationalService

router = APIRouter(prefix="/national", tags=["national"])


@router.get("", response_model=CityDetail)
def get_national(
    service: NationalService = Depends(get_national_service),
) -> Response:
    # Return the Redis-cached raw JSON directly: skip re-validating the
    # aggregate (with its full trend/history) through the response_model.
    return Response(
        content=service.national_detail_json(),
        media_type="application/json",
    )


@router.get("/housing", response_model=Page[HousingPriceByType])
def get_national_housing(
    service: NationalService = Depends(get_national_service),
) -> Page[HousingPriceByType]:
    return service.national_housing()
