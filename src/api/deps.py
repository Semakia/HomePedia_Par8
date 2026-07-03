"""FastAPI dependency providers wiring services to the Postgres Gold backend."""

from __future__ import annotations

from src.api.config import get_settings
from src.api.dependencies import get_engine, get_redis
from src.api.repositories.postgres import (
    PostgresArrondissementRepository,
    PostgresCityRepository,
    PostgresHousingRepository,
    PostgresMobilityRepository,
)
from src.api.services.arrondissement_service import ArrondissementService
from src.api.services.city_service import CityService
from src.api.services.housing_service import HousingService
from src.api.services.mobility_service import MobilityService
from src.api.services.national_service import NationalService


def get_city_service() -> CityService:
    schema = get_settings().gold_schema
    return CityService(PostgresCityRepository(get_engine(), schema), get_redis())


def get_national_service() -> NationalService:
    schema = get_settings().gold_schema
    engine = get_engine()
    return NationalService(
        PostgresCityRepository(engine, schema),
        PostgresHousingRepository(engine, schema),
        get_redis(),
    )


def get_housing_service() -> HousingService:
    schema = get_settings().gold_schema
    return HousingService(PostgresHousingRepository(get_engine(), schema))


def get_arrondissement_service() -> ArrondissementService:
    schema = get_settings().gold_schema
    return ArrondissementService(PostgresArrondissementRepository(get_engine(), schema))


def get_mobility_service() -> MobilityService:
    # Gares live in the fixed `mobility` schema (not under gold_schema).
    return MobilityService(PostgresMobilityRepository(get_engine()))
