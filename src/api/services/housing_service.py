"""Housing business logic (per-type price metrics)."""

from __future__ import annotations

from src.api.repositories.base import HousingRepository
from src.api.schemas.common import Page
from src.api.schemas.housing import HousingPriceByType


class HousingService:
    def __init__(self, repo: HousingRepository) -> None:
        self.repo = repo

    def list_prices(
        self, code_commune: str | None, type_local: str | None,
        page: int, size: int,
    ) -> Page[HousingPriceByType]:
        offset = (page - 1) * size
        items, total = self.repo.list_prices(code_commune, type_local, offset, size)
        return Page.build(items, total, page, size)
