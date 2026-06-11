"""Unit tests for the DVF Bronze ingestion slice (no network, no S3)."""

from __future__ import annotations

import pytest
import requests

from src.data_ingestion.loaders.s3_loader import bronze_key
from src.data_ingestion.sources.dvf_connector import DVFConnector
from src.data_ingestion.utils.retry_logic import retry


# --- bronze_key --------------------------------------------------------------
def test_bronze_key_full_year():
    assert bronze_key("dvf", "full.csv.gz", year=2024) == "dvf/year=2024/full.csv.gz"


def test_bronze_key_with_departement():
    key = bronze_key("dvf", "75.csv.gz", year=2024, departement="75")
    assert key == "dvf/year=2024/departement=75/75.csv.gz"


def test_bronze_key_strips_dataset_slashes():
    assert bronze_key("/dvf/", "f.gz", year=2024) == "dvf/year=2024/f.gz"


# --- DVF url / key resolution ------------------------------------------------
def test_source_url_full_vs_departement():
    assert DVFConnector._source_url(2024, None).endswith("/2024/full.csv.gz")
    assert DVFConnector._source_url(2024, "75").endswith("/2024/departements/75.csv.gz")


def test_dvf_bronze_key_resolution():
    assert DVFConnector._bronze_key(2023, None) == "dvf/year=2023/full.csv.gz"
    assert (
        DVFConnector._bronze_key(2023, "2A")
        == "dvf/year=2023/departement=2A/2A.csv.gz"
    )


# --- retry -------------------------------------------------------------------
def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    @retry(max_attempts=3, base_delay=0, max_delay=0, jitter=0, exceptions=(ValueError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_reraises_after_exhaustion():
    @retry(max_attempts=2, base_delay=0, max_delay=0, jitter=0, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        always_fails()


def test_retry_does_not_catch_unlisted_exceptions():
    calls = {"n": 0}

    @retry(max_attempts=3, base_delay=0, exceptions=(requests.RequestException,))
    def raises_type_error():
        calls["n"] += 1
        raise TypeError("not retried")

    with pytest.raises(TypeError):
        raises_type_error()
    assert calls["n"] == 1  # not retried
