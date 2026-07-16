"""API contract tests — router -> service -> schema, with fake repositories.

No database: the repositories are replaced via FastAPI dependency_overrides, so
these validate the HTTP contract (pagination, filtering, 404) independently of
the Gold tables being populated.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from src.api.deps import (
    get_city_service,
    get_housing_service,
    get_national_service,
)
from src.api.main import app
from src.api.repositories.base import CityRepository, HousingRepository
from src.api.schemas.city import CityDetail, CityMetrics, PriceTrendPoint
from src.api.schemas.housing import HousingPriceByType
from src.api.services.city_service import CityService
from src.api.services.housing_service import HousingService
from src.api.services.national_service import NationalService

PARIS = CityMetrics(
    code_commune="75056", nom_commune="Paris", code_departement="75",
    prix_m2_median=10000.0, nb_transactions=100,
)
LYON = CityMetrics(
    code_commune="69123", nom_commune="Lyon", code_departement="69",
    prix_m2_median=5000.0, nb_transactions=60,
)


class FakeCityRepo(CityRepository):
    def __init__(self, cities: list[CityMetrics]) -> None:
        self.cities = cities

    def list_cities(self, departement, query, sort, order, offset, limit):
        rows = self.cities
        if departement:
            rows = [c for c in rows if c.code_departement == departement]
        return rows[offset:offset + limit], len(rows)

    def get_city(self, code_commune):
        for c in self.cities:
            if c.code_commune == code_commune:
                return CityDetail(**c.model_dump(), trend=[
                    PriceTrendPoint(year=2024, month=1, prix_m2_median=9800.0,
                                    nb_transactions=8),
                ])
        return None

    def get_national(self):
        # Transaction-weighted mean of the fake cities' medians.
        tx = sum(c.nb_transactions for c in self.cities)
        prix = sum(
            (c.prix_m2_median or 0) * c.nb_transactions for c in self.cities
        ) / tx
        return CityDetail(
            code_commune="FR", nom_commune="France entière",
            code_departement="FR", prix_m2_median=prix, nb_transactions=tx,
            trend=[PriceTrendPoint(year=2024, month=1, prix_m2_median=prix,
                                   nb_transactions=tx)],
        )


class FakeHousingRepo(HousingRepository):
    def list_prices(self, code_commune, type_local, offset, limit):
        rows = [HousingPriceByType(
            code_commune="75056", type_local="Appartement",
            prix_m2_median=10500.0, nb_transactions=80,
        )]
        return rows[offset:offset + limit], len(rows)

    def list_prices_national(self):
        return [
            HousingPriceByType(code_commune="FR", type_local="Appartement",
                               prix_m2_median=8000.0, nb_transactions=140),
            HousingPriceByType(code_commune="FR", type_local="Maison",
                               prix_m2_median=3000.0, nb_transactions=90),
        ]


@pytest.fixture
def client():
    app.dependency_overrides[get_city_service] = lambda: CityService(
        FakeCityRepo([PARIS, LYON])
    )
    app.dependency_overrides[get_housing_service] = lambda: HousingService(
        FakeHousingRepo()
    )
    app.dependency_overrides[get_national_service] = lambda: NationalService(
        FakeCityRepo([PARIS, LYON]), FakeHousingRepo()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_cities_paginated(client):
    r = client.get("/api/v1/cities?size=1&page=1")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["nom_commune"] in {"Paris", "Lyon"}


def test_list_cities_filter_departement(client):
    r = client.get("/api/v1/cities?departement=69")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["code_commune"] == "69123"


def test_insee_fields_present_but_null(client):
    city = client.get("/api/v1/cities?departement=75").json()["items"][0]
    # Contract is stable before INSEE: fields exist, value is null.
    assert "population" in city and city["population"] is None
    assert "revenu_median" in city and city["revenu_median"] is None


def test_get_city_found_with_trend(client):
    r = client.get("/api/v1/cities/75056")
    assert r.status_code == 200
    body = r.json()
    assert body["nom_commune"] == "Paris"
    assert body["trend"][0]["year"] == 2024


def test_get_city_404(client):
    assert client.get("/api/v1/cities/00000").status_code == 404


def test_housing_prices(client):
    r = client.get("/api/v1/housing/prices?type_local=Appartement")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["type_local"] == "Appartement"


def test_invalid_order_rejected(client):
    assert client.get("/api/v1/cities?order=sideways").status_code == 422


def test_national_aggregate(client):
    r = client.get("/api/v1/national")
    assert r.status_code == 200
    body = r.json()
    assert body["code_commune"] == "FR"
    assert body["nom_commune"] == "France entière"
    # Transaction-weighted: (10000*100 + 5000*60) / 160 = 8125.
    assert body["prix_m2_median"] == 8125.0
    assert body["nb_transactions"] == 160
    assert len(body["trend"]) == 1


def test_national_housing(client):
    r = client.get("/api/v1/national/housing")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    types = {row["type_local"] for row in body["items"]}
    assert types == {"Appartement", "Maison"}
