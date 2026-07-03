"""Shared helper: municipal arrondissements of Paris / Lyon / Marseille.

DVF codes these three cities by *arrondissement* (75101-75120, 69381-69389,
13201-13216), and INSEE/FiLoSoFi expose their figures under the Melodi GEO type
`ARM-` (not `COM-`). Both the INSEE and FiLoSoFi connectors reuse this to also
land arrondissement-level data for the relevant departments.
"""

from __future__ import annotations

import requests

# Departments whose communes have municipal arrondissements.
ARR_DEPARTEMENTS = {"75", "69", "13"}

GEO_API_ARR_URL = (
    "https://geo.api.gouv.fr/communes"
    "?type=arrondissement-municipal"
    "&fields=code,nom,codeDepartement,codeRegion"
)


def fetch_arrondissements(departement: str, timeout: int = 15) -> list[dict]:
    """
    Return the municipal arrondissements of a department, or [] if none.

    One call returns all 45 French arrondissements municipaux; we filter to the
    requested department (handles the Métropole de Lyon, where a per-department
    commune listing would miss Lyon's arrondissements).
    """
    if departement not in ARR_DEPARTEMENTS:
        return []
    resp = requests.get(GEO_API_ARR_URL, timeout=timeout)
    resp.raise_for_status()
    return [a for a in resp.json() if a.get("codeDepartement") == departement]
