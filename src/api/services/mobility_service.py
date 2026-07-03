"""Mobility business logic (train stations point layer)."""

from __future__ import annotations

from src.api.repositories.base import MobilityRepository
from src.api.schemas.common import Page
from src.api.schemas.mobility import Gare


class MobilityService:
    def __init__(self, repo: MobilityRepository) -> None:
        self.repo = repo

    def list_gares(
        self, departement: str | None, code_commune: str | None,
        page: int, size: int,
    ) -> Page[Gare]:
        offset = (page - 1) * size
        items, total = self.repo.list_gares(departement, code_commune, offset, size)
        return Page.build(items, total, page, size)
