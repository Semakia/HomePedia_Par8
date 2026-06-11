"""Repository interfaces — the seam that lets the data source be swapped.

Today: PostgreSQL Gold tables (empty until silver_to_gold runs).
Routers/services depend ONLY on these abstractions, so swapping the backing
store later (or adding a cache) touches no business code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.api.schemas.city import CityDetail, CityMetrics
from src.api.schemas.housing import HousingPriceByType


class CityRepository(ABC):
    @abstractmethod
    def list_cities(
        self,
        departement: str | None,
        query: str | None,
        sort: str,
        order: str,
        offset: int,
        limit: int,
    ) -> tuple[list[CityMetrics], int]:
        """Return (page of cities, total count)."""

    @abstractmethod
    def get_city(self, code_commune: str) -> CityDetail | None:
        """Return a city with its price trend, or None if unknown."""


class HousingRepository(ABC):
    @abstractmethod
    def list_prices(
        self,
        code_commune: str | None,
        type_local: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[HousingPriceByType], int]:
        """Return (page of per-type housing metrics, total count)."""
