"""City business logic.

Thin today (pagination glue); the home for affordability (prix/m² vs INSEE
revenu_median) and ranking once INSEE data is available.
"""

from __future__ import annotations

from src.api.repositories.base import CityRepository
from src.api.schemas.city import CityDetail, CityMetrics
from src.api.schemas.common import Page


class CityService:
    def __init__(self, repo: CityRepository) -> None:
        self.repo = repo

    def list_cities(
        self, departement: str | None, query: str | None,
        sort: str, order: str, page: int, size: int,
    ) -> Page[CityMetrics]:
        offset = (page - 1) * size
        items, total = self.repo.list_cities(
            departement, query, sort, order, offset, size
        )
        return Page.build(items, total, page, size)

    def get_city(self, code_commune: str) -> CityDetail | None:
        return self.repo.get_city(code_commune)
