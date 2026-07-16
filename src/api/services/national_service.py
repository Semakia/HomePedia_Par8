"""France-wide aggregate business logic.

Serves the "France entière" stats view: a single national aggregate shaped
exactly like a city (``CityDetail``) plus the per-type housing split, so the
frontend reuses the whole per-city stats page unchanged.

Quantities (population, transactions, amenities) are exact SUMs; prices/income
are transaction/population-weighted means over every commune (Gold keeps only
per-commune medians, not raw transactions — a true statistical median would
need an ETL-side national row). The result only changes on ETL reload, so the
national ``CityDetail`` is Redis-cached as raw JSON — same pattern as the bulk
map feed in ``CityService`` — turning every hit after the first into an instant
serve shared across workers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.api.repositories.base import CityRepository, HousingRepository
from src.api.schemas.common import Page
from src.api.schemas.housing import HousingPriceByType

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)

_DETAIL_KEY = "national:detail"
_TTL_S = 3600  # seconds; refreshed lazily after expiry (Gold reloads on ETL)


class NationalService:
    def __init__(
        self,
        city_repo: CityRepository,
        housing_repo: HousingRepository,
        cache: redis.Redis | None = None,
    ) -> None:
        self.city_repo = city_repo
        self.housing_repo = housing_repo
        self.cache = cache

    def national_detail_json(self) -> str:
        """France-wide aggregate (CityDetail) as a serialized JSON string.

        Cached/returned as raw JSON so the ~500k-row aggregation runs at most
        once per TTL and hits never re-validate through Pydantic.
        """
        cached = self._cache_get(_DETAIL_KEY)
        if cached is not None:
            return cached
        payload = self.city_repo.get_national().model_dump_json()
        self._cache_set(_DETAIL_KEY, payload)
        return payload

    def national_housing(self) -> Page[HousingPriceByType]:
        rows = self.housing_repo.list_prices_national()
        return Page.build(rows, len(rows), 1, max(len(rows), 1))

    # --- Redis helpers: never let a cache outage break the request ----------
    def _cache_get(self, key: str) -> str | None:
        if self.cache is None:
            return None
        try:
            return self.cache.get(key)
        except Exception as exc:  # noqa: BLE001 - cache is best-effort
            logger.warning("national cache read failed (%s): %s", key, exc)
            return None

    def _cache_set(self, key: str, value: str) -> None:
        if self.cache is None:
            return
        try:
            self.cache.setex(key, _TTL_S, value)
        except Exception as exc:  # noqa: BLE001
            logger.warning("national cache write failed (%s): %s", key, exc)
