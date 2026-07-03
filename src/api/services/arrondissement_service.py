"""Arrondissement business logic (intra-city drill-down)."""

from __future__ import annotations

from src.api.repositories.base import ArrondissementRepository
from src.api.schemas.arrondissement import ArrondissementDetail, ArrondissementMetrics
from src.api.schemas.common import Page


class ArrondissementService:
    def __init__(self, repo: ArrondissementRepository) -> None:
        self.repo = repo

    def list_arrondissements(
        self, departement: str | None, code_commune_parent: str | None,
        sort: str, order: str, page: int, size: int,
    ) -> Page[ArrondissementMetrics]:
        offset = (page - 1) * size
        items, total = self.repo.list_arrondissements(
            departement, code_commune_parent, sort, order, offset, size
        )
        return Page.build(items, total, page, size)

    def get_arrondissement(self, code: str) -> ArrondissementDetail | None:
        return self.repo.get_arrondissement(code)
