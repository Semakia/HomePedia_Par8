"""Enrich the HOMEPEDIA OpenMetadata catalog beyond tables + quality.

Complements ``openmetadata_sync.py`` (which pushes data-quality results). This
adds the governance layer expected on a catalog:

  * **Owners** — a ``DataEngineering`` team owns every served table + DVF Silver.
  * **Tier tags** — Gold served tables are ``Tier.Tier1``; DVF Silver ``Tier.Tier2``.
  * **Glossary** — a ``HOMEPEDIA`` glossary of the business terms used in the UI.
  * **Lineage** — DVF Silver → the Gold ``market`` tables it feeds.

Idempotent: re-running skips what already exists. Auth uses the OM *admin*
login token (same approach as openmetadata_sync). Run from the repo root with
OM up:

    python -m src.data_governance.metadata.openmetadata_enrich
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

GOLD_DB = "homepedia_gold.homepedia_gold_dev"
DVF_FQN = "homepedia.silver.dvf.dvf_silver"

# Served Gold tables → tier. DVF Silver is the upstream logical table.
GOLD_TABLES = [
    f"{GOLD_DB}.market.city_metrics",
    f"{GOLD_DB}.market.arrondissement_metrics",
    f"{GOLD_DB}.market.city_price_trend",
    f"{GOLD_DB}.market.housing_price_by_type",
    f"{GOLD_DB}.demographics.commune_profile",
    f"{GOLD_DB}.mobility.commune_transport",
    f"{GOLD_DB}.mobility.gares",
    f"{GOLD_DB}.services.commune_equipements",
]

# DVF Silver feeds the market tables (its lineage children).
LINEAGE_FROM_DVF = [
    f"{GOLD_DB}.market.city_metrics",
    f"{GOLD_DB}.market.arrondissement_metrics",
    f"{GOLD_DB}.market.city_price_trend",
    f"{GOLD_DB}.market.housing_price_by_type",
]

TEAM_NAME = "DataEngineering"

GLOSSARY = "HOMEPEDIA"
GLOSSARY_TERMS = {
    "Accessibilite": "Années de revenu médian pour acheter un bien de surface "
    "médiane locale (affordability_years).",
    "AffordabilityClass": "Classe d'accessibilité : Très abordable / Abordable "
    "/ Tendu / Très tendu.",
    "DesserteClass": "Niveau de desserte ferroviaire d'une commune : Hub majeur "
    "/ Bien desservie / Desservie / Non desservie.",
    "SegmentDRG": "Classement SNCF d'une gare (a = grande, b = moyenne, c = petite).",
    "NiveauEquipement": "Niveau d'équipement BPE : Sous-équipée / Équipée / "
    "Bien équipée / Très équipée.",
    "Millesime": "Année de référence d'une source, parfois distincte de l'année "
    "DVF (insee_ref_year, revenu_ref_year).",
    "RollupArrondissement": "Agrégation des arrondissements (Paris/Lyon/Marseille) "
    "vers la commune mère (75056 / 69123 / 13055).",
}


class OMClient:
    def __init__(self, host: str | None = None) -> None:
        self.base = (host or os.getenv("OM_HOST", "http://localhost:8585")) + "/api/v1"
        self.token = self._login()

    def _req(
        self, path: str, method: str = "GET", body=None, ctype: str | None = None
    ) -> tuple[int, dict]:
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method)
        r.add_header("Content-Type", ctype or "application/json")
        if getattr(self, "token", None):
            r.add_header("Authorization", "Bearer " + self.token)
        try:
            resp = urllib.request.urlopen(r, timeout=60)
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read())
            except Exception:  # noqa: BLE001
                return exc.code, {}

    def _login(self) -> str:
        pw = base64.b64encode(
            os.getenv("OM_ADMIN_PASSWORD", "admin").encode()
        ).decode()
        email = os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org")
        _, body = self._req("/users/login", "POST", {"email": email, "password": pw})
        return body["accessToken"]

    # --- team / owner -------------------------------------------------------
    def ensure_team(self, name: str) -> str | None:
        code, body = self._req(f"/teams/name/{name}", "GET")
        if code < 400 and body.get("id"):
            return body["id"]
        code, body = self._req("/teams", "POST", {
            "name": name,
            "displayName": "Data Engineering",
            "teamType": "Group",
            "description": "Owns the HOMEPEDIA data platform (pipelines + served data).",
        })
        return body.get("id")

    def table(self, fqn: str) -> dict | None:
        code, body = self._req(
            f"/tables/name/{fqn}?fields=owners,tags", "GET"
        )
        return body if code < 400 and body.get("id") else None

    def _patch(self, table_id: str, ops: list[dict]) -> int:
        code, _ = self._req(
            f"/tables/{table_id}", "PATCH", ops,
            ctype="application/json-patch+json",
        )
        return code

    def set_owner(self, tbl: dict, team_id: str) -> str:
        owners = tbl.get("owners") or []
        if any(o.get("id") == team_id for o in owners):
            return "owner exists"
        op = {"op": "add",
              "path": "/owners/-" if owners else "/owners",
              "value": {"id": team_id, "type": "team"} if owners
              else [{"id": team_id, "type": "team"}]}
        return "owner set" if self._patch(tbl["id"], [op]) < 400 else "owner ERR"

    def set_tier(self, tbl: dict, tier: str) -> str:
        tag_fqn = f"Tier.{tier}"
        tags = tbl.get("tags") or []
        if any(t.get("tagFQN") == tag_fqn for t in tags):
            return "tier exists"
        op = {"op": "add",
              "path": "/tags/-" if tags else "/tags",
              "value": {"tagFQN": tag_fqn, "source": "Classification",
                        "labelType": "Manual", "state": "Confirmed"} if tags
              else [{"tagFQN": tag_fqn, "source": "Classification",
                     "labelType": "Manual", "state": "Confirmed"}]}
        return f"{tier} set" if self._patch(tbl["id"], [op]) < 400 else "tier ERR"

    # --- glossary -----------------------------------------------------------
    def ensure_glossary(self, name: str) -> None:
        self._req("/glossaries", "POST", {
            "name": name,
            "displayName": name,
            "description": "Termes métier HOMEPEDIA (accessibilité, desserte, "
            "équipements).",
        })

    def ensure_term(self, glossary: str, name: str, description: str) -> str:
        code, _ = self._req("/glossaryTerms", "POST", {
            "glossary": glossary, "name": name, "description": description,
        })
        return "created" if code < 400 else ("exists" if code == 409 else f"ERR {code}")

    # --- lineage ------------------------------------------------------------
    def add_lineage(self, from_id: str, to_id: str) -> str:
        code, _ = self._req("/lineage", "PUT", {
            "edge": {
                "fromEntity": {"id": from_id, "type": "table"},
                "toEntity": {"id": to_id, "type": "table"},
            }
        })
        return "linked" if code < 400 else f"ERR {code}"


def main() -> None:
    load_dotenv()
    om = OMClient()

    team_id = om.ensure_team(TEAM_NAME)
    print(f"[team] {TEAM_NAME} -> {team_id}")

    # Owners + tiers on every served table (+ DVF Silver as Tier2 upstream).
    targets = [(fqn, "Tier1") for fqn in GOLD_TABLES] + [(DVF_FQN, "Tier2")]
    tbl_ids: dict[str, str] = {}
    for fqn, tier in targets:
        tbl = om.table(fqn)
        if not tbl:
            print(f"[skip] not cataloged: {fqn}")
            continue
        tbl_ids[fqn] = tbl["id"]
        owner = om.set_owner(tbl, team_id) if team_id else "no team"
        tier_s = om.set_tier(tbl, tier)
        print(f"[table] {fqn.split('.', 2)[-1]:35s} {owner:12s} {tier_s}")

    # Glossary + terms.
    om.ensure_glossary(GLOSSARY)
    for name, desc in GLOSSARY_TERMS.items():
        print(f"[term] {name:22s} {om.ensure_term(GLOSSARY, name, desc)}")

    # Lineage: DVF Silver -> market tables.
    if DVF_FQN in tbl_ids:
        for fqn in LINEAGE_FROM_DVF:
            if fqn in tbl_ids:
                r = om.add_lineage(tbl_ids[DVF_FQN], tbl_ids[fqn])
                print(f"[lineage] dvf_silver -> {fqn.split('.')[-1]:28s} {r}")
    else:
        print("[lineage] DVF Silver not cataloged — run openmetadata_sync --dataset dvf first")


if __name__ == "__main__":
    main()
