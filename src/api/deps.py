"""FastAPI dependency providers wiring services to the Postgres Gold backend."""

from __future__ import annotations

from src.api.dependencies import get_engine
from src.api.repositories.postgres import (
    PostgresCityRepository,
    PostgresHousingRepository,
)
from src.api.services.city_service import CityService
from src.api.services.housing_service import HousingService


def get_city_service() -> CityService:
    return CityService(PostgresCityRepository(get_engine()))


def get_housing_service() -> HousingService:
    return HousingService(PostgresHousingRepository(get_engine()))
