"""Mobility response schemas (Gold mobility.gares).

Geolocated train stations, served as a point layer for the map. `segment_drg`
is the SNCF traffic segment (A = largest hubs … C = small stations).
"""

from __future__ import annotations

from pydantic import BaseModel


class Gare(BaseModel):
    code_uic: str
    nom_gare: str
    code_commune: str | None = None
    segment_drg: str | None = None  # A | B | C (SNCF traffic tier)
    frequentation: int | None = None  # yearly passengers
    frequentation_year: int | None = None
    longitude: float | None = None
    latitude: float | None = None
