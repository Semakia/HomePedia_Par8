# HOMEPEDIA — Gouvernance des données

Ce document décrit la gouvernance de la plateforme de données HOMEPEDIA :
provenance, catalogue, qualité, documentation, rôles & accès, rétention et
traçabilité (lineage). Il fait le lien entre les artefacts déclaratifs
(`config/data_quality/*.yaml`, `src/data_governance/policies/*.yml`) et les
outils qui les appliquent (moteur de qualité, OpenMetadata).

---

## 1. Périmètre & classification

HOMEPEDIA agrège des **sources publiques ouvertes** à la maille communale pour
mesurer l'accessibilité immobilière en France :

| Source | Fournisseur | Contenu | Millésime |
|---|---|---|---|
| DVF | data.gouv (geo-dvf) | Mutations immobilières | 2021 → 2025 |
| Recensement | INSEE (Melodi) | Population, structure par âge/sexe | 2022 |
| FiLoSoFi | INSEE | Revenu médian disponible | 2023 |
| Gares & fréquentation | SNCF (Opendatasoft) | Desserte ferroviaire | 2024 |
| BPE | INSEE | Équipements / services | 2024 |

**Classification : `public`.** Toutes les données sont ouvertes et agrégées à la
commune — **aucune donnée personnelle** n'est stockée. La gouvernance porte donc
sur l'**intégrité opérationnelle** (qui peut muter une couche, traçabilité,
qualité) plutôt que sur la confidentialité.

---

## 2. Architecture médaillon & provenance

```
Sources ──► BRONZE (S3, brut immuable) ──► SILVER (S3, Parquet nettoyé) ──► GOLD (PostgreSQL servi)
```

| Couche | Stockage | Format | Provenance / garanties |
|---|---|---|---|
| **Bronze** | `s3://homepedia-bronze` | JSON / CSV.gz bruts | Chaque dépôt est accompagné d'un `_manifest.json` (sha256, source, horodatage) → traçabilité et reproductibilité. Immuable : une ré-ingestion écrit un nouvel objet. |
| **Silver** | `s3://homepedia-silver` | Parquet partitionné `year` / `code_departement` | Nettoyage, typage, déduplication. *Dynamic partition overwrite* : une partition `(année, dépt)` est remplacée en place. |
| **Gold** | PostgreSQL `homepedia_gold_dev` | Tables relationnelles | Écriture Spark JDBC `truncate + reload` (la structure et les commentaires survivent). Servi en lecture seule par l'API. |

### Schémas Gold servis

| Schéma | Tables | Domaine |
|---|---|---|
| `market` | `city_metrics`, `arrondissement_metrics`, `city_price_trend`, `housing_price_by_type` | Prix, accessibilité |
| `demographics` | `commune_profile` | Population, âges |
| `mobility` | `commune_transport`, `gares` | Desserte ferroviaire |
| `services` | `commune_equipements` | Équipements (BPE) |

---

## 3. Rôles, ownership & accès (RBAC)

Le contrôle d'accès est déclaré dans
[`src/data_governance/policies/access_policies.yml`](../src/data_governance/policies/access_policies.yml)
et appliqué par
[`src/data_governance/security/rb_access.py`](../src/data_governance/security/rb_access.py)
(`AccessControl.can(role, resource, action)`, matching wildcard `gold.*`).

| Rôle | Bronze | Silver | Gold | Rapports qualité | Catalogue |
|---|:--:|:--:|:--:|:--:|:--:|
| `data_engineer` | rwd | rwd | rwd | rw | rw |
| `ingestion_service` (Airflow/Spark) | rw | rw | rw | rw | — |
| `data_analyst` | — | — | r | r | r |
| `api_service` (FastAPI) | — | — | r | — | — |
| `catalog_viewer` | — | — | — | — | r |

> *r = read, w = write, d = delete.*

**Ownership.** Chaque domaine Gold a un propriétaire déclaré dans OpenMetadata
(équipe *Data Engineering*) ; le dataset DVF Silver de même. Les utilisateurs
finaux du produit n'accèdent **jamais** directement à la plateforme : ils passent
par l'**API Gold publique en lecture seule** (qui tourne sous `api_service`).

Vérification en ligne de commande :

```bash
python -m src.data_governance.security.rb_access ingestion_service gold.market write   # ALLOW
python -m src.data_governance.security.rb_access api_service silver read                # DENY
```

---

## 4. Catalogue de données (OpenMetadata)

**OpenMetadata 1.12.10** (déployé depuis `iac/docker/dev/openmetadata/`) est le
système de référence du catalogue.

- **Ingestion** : le connecteur Postgres catalogue les **4 schémas Gold** (8
  tables) via `iac/docker/dev/openmetadata/ingest_gold.yaml`. Le DVF Silver est
  représenté comme une **table logique** (non stockée en base).
- **Descriptions** : posées à la source par
  [`src/data_governance/metadata/gold_column_comments.sql`](../src/data_governance/metadata/gold_column_comments.sql)
  (`COMMENT ON TABLE/COLUMN`, 100 colonnes). Durables car les writers Gold
  utilisent `truncate` (pas de DROP). OpenMetadata les lit à la ré-ingestion.
- **Enrichissement** (owners, tiers, glossaire, lineage) : poussé par le module
  de synchronisation `src/data_governance/metadata/openmetadata_sync.py`
  (authentification via le token admin, voir §7).

---

## 5. Qualité des données

Moteur **déclaratif** maison, découplé de Spark :

- **Règles** en YAML dans `config/data_quality/` : `gold_market.yaml` (8
  contrôles), `gold_demographics.yaml` (7), `gold_mobility.yaml` (6),
  `gold_services.yaml` (6), plus le DVF Silver.
- **Moteur** :
  [`quality_monitor.py`](../src/data_governance/quality/quality_monitor.py)
  (`QualityMonitor`, `CheckResult`) +
  [`data_quality_reporter.py`](../src/data_governance/quality/data_quality_reporter.py),
  *source-aware* : lit le Parquet Silver (S3) **ou** le Gold servi (JDBC
  Postgres) selon la clé `source:` de la règle. Option `ignore_nulls` pour les
  colonnes nullables.
- **Types de contrôles** : volume (`not_empty`), complétude de clés
  (`keys_complete`), unicité de PK (`pk_unique`), format (regex, ex. code
  commune), domaines de valeurs (`set`, ex. `desserte_class`,
  `niveau_equipement`), bornes (`range`, ex. distance ∈ [0,150]).
- **Rapports** : écrits sur `s3://homepedia-silver/_quality/<dataset>/run=*.json`.
- **Gates ETL** : chaque DAG exécute son contrôle qualité après le chargement
  Gold (`housing`, `mobility_etl`, `amenities_etl`).
- **Pont vers OpenMetadata** :
  [`openmetadata_sync.py`](../src/data_governance/metadata/openmetadata_sync.py)
  lit le dernier rapport S3 et publie des **TestCases + résultats** sur la table
  cataloguée correspondante. État : DVF, market, demographics, mobility,
  services — tous au vert.

---

## 6. Rétention & cycle de vie

Politique déclarée dans
[`src/data_governance/policies/retention_policies.yml`](../src/data_governance/policies/retention_policies.yml).

| Couche | Rétention | Application |
|---|---|---|
| Bronze | **730 j** (immuable) | Lifecycle S3 ; assez pour rejouer/auditer un build. |
| Silver | **indéfinie** | Tous les millésimes servent les séries temporelles. |
| Gold | **courant** | Seul le dernier reload est servi ; l'historique vit dans les tables (`city_price_trend`, `metrics_by_year`). |
| Rapports qualité | **180 j** | ~6 mois d'historique qualité. |
| Catalogue OM | **indéfinie** | Système de référence gouvernance. |

---

## 7. Traçabilité (lineage)

Le lineage **Bronze → Silver → Gold** est poussé dans OpenMetadata pour rendre
visible le flux de bout en bout :

```
DVF (bronze) ──► DVF Silver ──► market.city_metrics / arrondissement_metrics / city_price_trend / housing_price_by_type
INSEE / FiLoSoFi ──► Silver ──► market.* (enrichissement) + demographics.commune_profile
SNCF ──► Silver ──► mobility.commune_transport + mobility.gares
BPE ──► Silver ──► services.commune_equipements
```

La provenance fine côté Bronze est assurée par les `_manifest.json` (sha256).

---

## 8. Glossaire métier

| Terme | Définition |
|---|---|
| **Accessibilité (`affordability_years`)** | Nombre d'années de revenu médian nécessaires pour acheter un bien de surface médiane locale. |
| **`affordability_class`** | Classe dérivée : *Très abordable / Abordable / Tendu / Très tendu*. |
| **`desserte_class`** | Niveau de desserte ferroviaire d'une commune : *Hub majeur / Bien desservie / Desservie / Non desservie*. |
| **Segment DRG** | Classement SNCF d'une gare (a = grande, b = moyenne, c = petite). |
| **`niveau_equipement`** | Niveau d'équipement BPE d'une commune : *Sous-équipée / Équipée / Bien équipée / Très équipée*. |
| **Millésime** | Année de référence d'une source (peut différer de l'année DVF ; colonnes `insee_ref_year`, `revenu_ref_year`). |
| **Rollup arrondissement** | Agrégation des arrondissements (Paris/Lyon/Marseille) vers la commune mère (75056 / 69123 / 13055). |

---

## 9. Opérations gouvernance

```bash
# Contrôle qualité (dans le conteneur Spark) — écrit le rapport S3
spark-submit src/data_governance/quality/data_quality_reporter.py --rules config/data_quality/gold_market.yaml

# Publier les résultats qualité vers OpenMetadata (depuis l'hôte)
python -m src.data_governance.metadata.openmetadata_sync --dataset gold_city_metrics

# Vérifier une autorisation RBAC
python -m src.data_governance.security.rb_access data_analyst gold.services read

# (Ré)appliquer les descriptions de colonnes à la source, puis ré-ingérer dans OM
psql "$DATABASE_URL" -f src/data_governance/metadata/gold_column_comments.sql
```

> Détails de déploiement OpenMetadata (ports, token admin, ingestion one-off) :
> voir `iac/docker/dev/openmetadata/README.md`.
