# HOMEPEDIA

![Epitech](https://img.shields.io/badge/Epitech-T--DAT--902-1d4ed8)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.10-017CEE?logo=apacheairflow&logoColor=white)
![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-E25A1C?logo=apachespark&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)

**HOMEPEDIA** aide un jeune actif à décider **où acheter un bien en France**. La
difficulté n'est pas le manque de données ouvertes, mais leur lecture : un prix au
m² seul ne dit pas si un quartier est *abordable au regard des revenus*, *bien
desservi*, *équipé* ou *peuplé de gens comme moi*. La plateforme croise ces axes et
les traduit en une décision, sur une carte interactive et des tableaux de bord.

Le projet est bâti sur une **architecture médaillon** (Bronze → Silver → Gold),
orchestrée par Airflow, exposée par une API FastAPI et consommée par un front
Next.js.

> Projet Epitech **T-DAT-902** (« Big Data ») — groupe **PAR_5**.
> Rapport détaillé (visualisations, métriques, règles métier) :
> [docs/rapport/rapport-du-projet.pdf](docs/rapport/rapport-du-projet.pdf).
> Schéma de flux : [docs/diagrams/data_flow_archi.png](docs/diagrams/data_flow_archi.png).

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalites)
- [Architecture et données](#architecture-et-donnees)
- [Stack technique](#stack-technique)
- [Démarrage rapide (dev)](#demarrage-rapide)
- [Pipelines de données](#pipelines-de-donnees)
- [Déploiement (prod)](#deploiement)
- [Structure du dépôt](#structure-du-depot)
- [Tests et qualité](#tests-et-qualite)
- [Documentation](#documentation)

---

<a id="vue-densemble"></a>

## Vue d'ensemble

HOMEPEDIA est une solution complète de traitement de données immobilières et
territoriales : ingestion de plusieurs sources ouvertes, nettoyage distribué avec
Spark, agrégation dans une couche Gold requêtable, le tout orchestré par Airflow et
restitué dans une application web. L'objectif : transformer des indicateurs bruts
(prix, revenus, gares, équipements, démographie) en une **aide à la décision**
lisible pour un non-expert.

<a id="fonctionnalites"></a>

## Fonctionnalités

- **Cartographe** — choroplèthe de France coloré par un *score de correspondance*
  personnalisé (0–100) que l'utilisateur pondère lui-même (budget / transport /
  services / jeunes actifs), + 6 modes de lecture et un calque des gares.
- **Fiche commune** — score détaillé, surface atteignable avec le budget saisi,
  tendance de prix, transport, équipements, pyramide d'âge ; drill-down aux
  arrondissements pour Paris / Lyon / Marseille.
- **Statistiques** — 7 graphiques (prix mensuel & annuel, types de biens, profil de
  population, services, radar de correspondance).
- **Tableau** comparatif triable / exportable des arrondissements.
- **Analyse textuelle** — synthèse rédigée par un moteur à règles (déterministe,
  explicable, sans LLM).

<a id="architecture-et-donnees"></a>

## Architecture et données

Quatre **domaines** issus de sources ouvertes, agrégés dans la couche **Gold** :

| Domaine | Source | Schéma Gold |
|---|---|---|
| Prix & abordabilité | DVF (Etalab) × revenus FiLoSoFi (INSEE) | `market` |
| Démographie | Recensement INSEE | `demographics` |
| Transport | Gares SNCF (open data) | `mobility` |
| Services & commerces | Équipements BPE (INSEE) | `services` |

Flux : **Bronze** (données brutes sur object store S3) → **Silver** (nettoyage &
normalisation Spark, stocké en Parquet) → **Gold** (agrégats par commune/année
pré-calculés dans PostgreSQL, servis par l'API).

<a id="stack-technique"></a>

## Stack technique

| Couche | Techno | Port local |
|---|---|---|
| Object store (Bronze/Silver) | MinIO (S3) | 9000 / 9001 (console) |
| Gold relationnel + métadonnées Airflow | PostgreSQL 16 | 5432 |
| Cache | Redis 7 | 6379 |
| Moteur ETL Silver/Gold | Spark 3.5 (master + worker) | 7077 / 8090 (UI) |
| API | FastAPI | 8000 |
| Frontend | Next.js 16 (App Router) | 3000 |
| Orchestration | Airflow 2.10 (LocalExecutor) | 8080 |
| Gouvernance (catalogue + qualité) | OpenMetadata | 8585 |

<a id="demarrage-rapide"></a>

## Démarrage rapide (dev)

### Prérequis
- Docker + Docker Compose
- [Task](https://taskfile.dev) (`task --version`) — recommandé
- Python 3.12 (tests/lint hors conteneur), Node ≥ 22 (frontend)

### 1. Data plane + API

```bash
task init          # crée .env depuis .env.dist
task up            # build + démarre minio, postgres, redis, spark, api
task airflow:up    # (optionnel) Airflow, une fois le data plane up
```

Points d'entrée :
- API + Swagger : http://localhost:8000/docs · Santé : `/health` · Readiness : `/ready`
- MinIO console : http://localhost:9001 (`minioadmin` / `minioadmin`)
- Spark master UI : http://localhost:8090
- Airflow : http://localhost:8080 (`admin` / `admin`)

### 2. Frontend

```bash
cd frontend
npm install
npm run db:migrate && npm run db:seed   # base comptes SQLite + comptes de démo
npm run dev                             # http://localhost:3000
```

Voir [frontend/README.md](frontend/README.md) pour la config (`AUTH_SECRET`,
`NEXT_PUBLIC_API_URL`) et les comptes de démo.

### 3. Gouvernance (optionnel)

```bash
task openmetadata:up     # http://localhost:8585 (~6 Go RAM Docker requis)
```

### Sans Task (compose brut)

```bash
docker compose -f iac/docker/dev/docker-compose.yml up -d --build
docker compose -f iac/docker/dev/airflow/docker-compose.yml up -d
```

<a id="pipelines-de-donnees"></a>

## Pipelines de données

Trois DAGs Airflow, planifiés au début de chaque mois (horaires décalés), exécutent
Bronze → Silver → Gold pour leur domaine :

| DAG | Domaine | Fichier |
|---|---|---|
| `housing_etl` | Prix DVF + abordabilité (+ démographie) | [airflow/dags/housing.py](airflow/dags/housing.py) |
| `mobility_etl` | Gares SNCF / desserte | [airflow/dags/mobility.py](airflow/dags/mobility.py) |
| `amenities_etl` | Équipements BPE / services | [airflow/dags/amenities.py](airflow/dags/amenities.py) |

Les descriptions sont externalisées en Markdown dans
[airflow/dags/config/](airflow/dags/config/). Chargement initial des sources :
scripts de backfill dans [scripts/](scripts/).

<a id="deploiement"></a>

## Déploiement (prod)

- **Images** : 4 images publiées sur **GHCR** par CI — `api`, `frontend`, `spark`,
  `airflow`.
- **VPS** (plan de service) : Caddy (HTTPS auto via nip.io), API, frontend, Redis et
  Airflow ; réutilise un PostgreSQL Gold existant sur l'hôte.
- **VM GCP Spark** (plan de données, à la demande) : une VM Compute Engine que
  **Airflow démarre avant chaque run puis arrête** (maîtrise des coûts) ; elle
  exécute `spark-submit`, lit S3 et écrit le Gold sur le VPS.
- **CI/CD** : [.github/workflows/deploy.yml](.github/workflows/deploy.yml) construit,
  pousse, puis met à jour le VPS (les secrets `.env.prod` / clés sont injectés en
  base64 depuis les secrets GitHub).

Détails et provisioning : [docs/hep-docs/DEPLOYMENT.md](docs/hep-docs/DEPLOYMENT.md).

<a id="structure-du-depot"></a>

## Structure du dépôt

```
src/api/                # FastAPI (config, routers, dépendances) — sert la couche Gold
src/data_ingestion/     # connecteurs sources → Bronze
src/data_processing/    # ETL Spark Bronze → Silver, qualité, agrégations
src/analytics/          # couche Gold (schémas & pipelines PostgreSQL)
src/data_governance/    # métadonnées, qualité, sécurité
airflow/dags/           # DAGs ETL (housing / mobility / amenities) + config .md
frontend/               # application Next.js (carte, stats, tableau, analyse)
iac/docker/dev/         # stack docker compose locale (data plane, Airflow, OpenMetadata)
iac/docker/prod/        # images & compose prod (api, frontend, spark, airflow, vps, gcp-vm)
iac/scripts/            # bootstrap (buckets S3, déploiement)
scripts/                # backfills DVF / FiLoSoFi / BPE
docs/hep-docs/          # documentation (déploiement, gouvernance, API, logique Silver…)
docs/rapport/           # rapport du projet (HTML source + PDF)
tests/                  # pytest
```

<a id="tests-et-qualite"></a>

## Tests et qualité

```bash
task test       # pytest
task lint       # ruff
task fmt        # black + ruff --fix
task config     # valide la config compose (dev + airflow)
task            # liste toutes les commandes
```

<a id="documentation"></a>

## Documentation

- Déploiement & infra : [docs/hep-docs/DEPLOYMENT.md](docs/hep-docs/DEPLOYMENT.md)
- Gouvernance des données : [docs/hep-docs/DATA_GOVERNANCE.md](docs/hep-docs/DATA_GOVERNANCE.md)
- Référence API : [docs/hep-docs/API_REFERENCE.md](docs/hep-docs/API_REFERENCE.md)
- Logique Silver DVF : [docs/hep-docs/silver_dvf_logic.md](docs/hep-docs/silver_dvf_logic.md)
- Fiche ville (métriques) : [docs/hep-docs/fiche_ville.md](docs/hep-docs/fiche_ville.md)
- Roadmap : [docs/hep-docs/ROADMAP.md](docs/hep-docs/ROADMAP.md)
- **Rapport du projet** : [docs/rapport/rapport-du-projet.pdf](docs/rapport/rapport-du-projet.pdf)

---

*Epitech · MSc Pro — Promotion 2026 · Projet T-DAT-902 · groupe PAR_5.*
