"""City business logic.

Thin today (pagination glue); the home for affordability (prix/m² vs INSEE
revenu_median) and ranking once INSEE data is available.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.api.repositories.base import CityRepository
from src.api.schemas.city import CityDetail, CityMetrics
from src.api.schemas.common import Page

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)

# The full-France map feed (unfiltered, large page) is a ~7s/23MB enriched
# query against the remote Gold DB, but it only changes on ETL. Caching it in
# Redis turns every load after the first into an instant hit, shared across
# workers.
BULK_MIN_SIZE = 1000
_BULK_TTL_S = 3600  # seconds; refreshed lazily after expiry (Gold reloads on ETL)


class CityService:
    def __init__(
        self,
        repo: CityRepository,
        cache: "redis.Redis | None" = None,
    ) -> None:
        self.repo = repo
        self.cache = cache

    @staticmethod
    def is_bulk(
        departement: str | None, query: str | None, page: int, size: int
    ) -> bool:
        """The unfiltered first page at a bulk size = the full-France map pull."""
        return (
            departement is None and query is None
            and page == 1 and size >= BULK_MIN_SIZE
        )

    def list_cities(
        self,
        departement: str | None,
        query: str | None,
        sort: str,
        order: str,
        page: int,
        size: int
    ) -> Page[CityMetrics]:
        """
        Paginated list of cities, optionally filtered by departement or name.
        Args:
            departement: 2-3 char code (e.g. "75" or "2A") to filter by
             departement.
            query: Case-insensitive substring search on city name
            sort: Column to sort by (e.g. "prix_m2_median")
            order: "asc" or "desc"
            page: 1-based page number
            size: Number of items per page
        Returns:
            Page[CityMetrics]: Paginated list of cities with metrics.
        """
        offset = (page - 1) * size
        items, total = self.repo.list_cities(
            departement, query, sort, order, offset, size
        )
        return Page.build(items, total, page, size)

    def list_cities_json(
        self,
        sort: str,
        order: str,
        size: int
    ) -> str:
        """
        Bulk map feed as a serialized JSON string, Redis-cached.

        We cache and return the *raw JSON* (never re-parsing it into 32k
        Pydantic models) because that validation — not the SQL — is the real
        cost on a hit. The router streams this straight to the client.
        """
        key = f"cities:bulk:{sort}:{order}:{size}"
        if self.cache is not None:
            cached = self._cache_get_raw(key)
            if cached is not None:
                return cached

        items, total = self.repo.list_cities(None, None, sort, order, 0, size)
        payload = Page.build(items, total, 1, size).model_dump_json()
        if self.cache is not None:
            self._cache_set_raw(key, payload)
        return payload

    # --- Redis helpers: never let a cache outage break the request ----------
    def _cache_get_raw(self, key: str) -> str | None:
        try:
            return self.cache.get(key)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 - cache is best-effort
            logger.warning("city cache read failed (%s): %s", key, exc)
            return None

    def _cache_set_raw(self, key: str, value: str) -> None:
        try:
            self.cache.setex(key, _BULK_TTL_S, value)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("city cache write failed (%s): %s", key, exc)

    def get_city(self, code_commune: str) -> CityDetail | None:
        return self.repo.get_city(code_commune)
