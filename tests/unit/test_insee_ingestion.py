"""Unit tests for the INSEE Bronze ingestion slice."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.data_ingestion.loaders.s3_loader import bronze_key
from src.data_ingestion.sources.insee_connector import InseeConnector


def test_insee_bronze_key_resolution():
    assert (
        InseeConnector._bronze_key(2022, "01")
        == "insee/year=2022/departement=01/population.json"
    )
    assert (
        InseeConnector._bronze_key(2020, "69")
        == "insee/year=2020/departement=69/population.json"
    )


@patch("src.data_ingestion.sources.insee_connector.requests.get")
def test_fetch_communes(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"code": "01001", "nom": "L'Abergement-Clémenciat", "codeDepartement": "01", "codeRegion": "84"},
        {"code": "01002", "nom": "L'Abergement-de-Varey", "codeDepartement": "01", "codeRegion": "84"},
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    connector = InseeConnector()
    communes = connector._fetch_communes("01")

    assert len(communes) == 2
    assert communes[0]["code"] == "01001"
    assert communes[0]["nom"] == "L'Abergement-Clémenciat"
    assert communes[0]["codeDepartement"] == "01"
    assert communes[0]["codeRegion"] == "84"
    mock_get.assert_called_once_with(
        "https://geo.api.gouv.fr/departements/01/communes?fields=code,nom,codeDepartement,codeRegion",
        timeout=15
    )


@patch("src.data_ingestion.sources.insee_connector.requests.get")
def test_fetch_melodi_batch(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "observations": [
            {"codGeo": "COM-01001", "timePeriod": "2022", "obsValue": 780},
            {"codGeo": "COM-01002", "timePeriod": "2022", "obsValue": 250},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    connector = InseeConnector()
    observations = connector._fetch_melodi_batch(["01001", "01002"], 2022)

    assert len(observations) == 2
    assert observations[0]["codGeo"] == "COM-01001"
    assert observations[0]["obsValue"] == 780
    
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == "https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC"
    assert ("TIME_PERIOD", "2022") in kwargs["params"]
    assert ("GEO", "COM-01001") in kwargs["params"]
    assert ("GEO", "COM-01002") in kwargs["params"]
