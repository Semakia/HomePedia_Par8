"""Repository interfaces — the seam that lets the data source be swapped.

Today: PostgreSQL Gold tables (empty until silver_to_gold runs).
Routers/services depend ONLY on these abstractions, so swapping the backing
store later (or adding a cache) touches no business code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.api.schemas.arrondissement import ArrondissementDetail, ArrondissementMetrics
from src.api.schemas.city import CityDetail, CityMetrics
from src.api.schemas.housing import HousingPriceByType
from src.api.schemas.mobility import Gare


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

    @abstractmethod
    def get_national(self) -> CityDetail:
        """Return the France-wide aggregate as a synthetic CityDetail.

        Quantities (population, transactions, amenities) are exact SUMs;
        prices/income are transaction/population-weighted means over every
        commune. Carries the aggregated per-year history and monthly trend.
        """


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

    @abstractmethod
    def list_prices_national(self) -> list[HousingPriceByType]:
        """Return the France-wide per-type (Maison/Appartement) aggregate."""


class ArrondissementRepository(ABC):
    @abstractmethod
    def list_arrondissements(
        self,
        departement: str | None,
        code_commune_parent: str | None,
        sort: str,
        order: str,
        offset: int,
        limit: int,
    ) -> tuple[list[ArrondissementMetrics], int]:
        """Return (page of arrondissements headline metrics, total count)."""

    @abstractmethod
    def get_arrondissement(self, code: str) -> ArrondissementDetail | None:
        """Return an arrondissement with its per-year history, or None."""


class MobilityRepository(ABC):
    @abstractmethod
    def list_gares(
        self,
        departement: str | None,
        code_commune: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Gare], int]:
        """Return (page of geolocated train stations, total count)."""
