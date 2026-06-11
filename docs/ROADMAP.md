# HOMEPEDIA — Roadmap

Suivi de l'avancement par couche de l'architecture médaillon
(Bronze → Silver → Gold) orchestrée par Airflow.
Voir [docs/README.md](README.md) (archi cible) et [docs/data_flow_archi.png](data_flow_archi.png).

> Légende : `[x]` fait · `[~]` en cours · `[ ]` à faire

---

## 0. Socle & plateforme
- [x] Stack docker compose dev (MinIO, Postgres, Redis, Spark, API)
- [x] Compose Airflow (LocalExecutor) + DAG smoke
- [x] Contrat de config `.env.dist` + chargement `.env`
- [x] Dépendances (`requirements/*`), `taskfile`, `.gitignore`, `pyproject`
- [x] Storage switch MinIO ⇄ Amazon S3 (par config)
- [ ] CI : tests + lint + build images (workflow `data-quality-checks.yml` à remplir)
- [ ] Pre-commit hooks (ruff/black) actifs

## 1. Ingestion (sources → Bronze S3)
- [x] **DVF** (prix immobiliers) — connecteur streaming + manifest de provenance
- [ ] **INSEE communes** — référentiel commune/département/région (clé de jointure)
- [ ] **INSEE** population / revenus / emploi
- [ ] **COG** — mapping code INSEE ↔ département ↔ région
- [ ] **SNCF / transport** — gares & dessertes
- [ ] **Mapbox / géocodage** — lat/lon, isochrones
- [ ] **Scraping SeLoger/PAP** — annonces *(si volume « big data » exigé)*
- [ ] Socle commun : `metadata_registrar` (catalogue), `schema_validator`, ingestion incrémentale

## 2. Silver (Bronze → Silver, Spark ETL)
- [ ] Job Spark générique lisant `s3a://` (jars hadoop-aws déjà dans l'image)
- [ ] `housing_dvf_etl` — typage, nettoyage, dédup, prix au m², filtres aberrants, normalisation géo
- [ ] `employment_etl` + autres transformations
- [ ] Écriture **Parquet partitionné** en Silver
- [ ] Contrôles qualité in-ligne (schema / completeness / anomaly)

## 3. Gold (Silver → couche requête)
- [ ] **PostgreSQL** — schéma analytique (`housing_prices`, `city_metrics`…), migrations, procédures
- [ ] Agrégations pré-calculées (`affordability_index`, `city_metrics`)
- [ ] **Redis** — warm cache des vues pré-calculées
- [ ] **Discipline volume** : tables de détail partitionnées (mois/région) + index ; pré-agrégation faite dans Spark, pas d'OLAP live
- [ ] *(escalade si besoin only)* DuckDB sur Parquet (analytique interactif) → ClickHouse (dernier recours) ; ES si full-text réel

## 4. API (FastAPI)
- [x] Squelette + `/health` + `/ready`
- [ ] Connexion réelle Gold (SQLAlchemy) → brancher `housing` sur des vraies données
- [ ] Routers : `cities`, `employment`, `transport`, `search`, `admin`
- [ ] Schémas Pydantic, pagination, gestion d'erreurs, rate-limit, CORS prod
- [ ] *(si requis)* auth JWT / RBAC

## 5. Frontend
- [ ] Trancher **Streamlit vs Next.js**
- [ ] Pages : overview, explorateur de villes, carte, affordability, recherche
- [ ] Client API + cache

## 6. Orchestration (Airflow)
- [x] DAG `homepedia_etl` (structure : ingest → silver → gold → quality → cache)
- [ ] Brancher `_ingest` sur les connecteurs réels (boucle départements)
- [ ] `SparkSubmitOperator` pour Silver
- [ ] Load Gold + refresh cache (tâches réelles)
- [ ] DAGs `data_quality` et `governance`
- [ ] Connections / Variables Airflow (S3, Postgres, Spark)

## 7. Gouvernance & qualité
- [ ] Data quality (Great Expectations ou règles maison) branchée dans les DAGs
- [ ] Lineage / catalogue (`metadata_store`, `catalog`, `column_profiler`)
- [ ] RBAC (`rb_access`), RGPD (anonymisation), rétention, audit log
- [ ] Alertes / monitoring (`config/monitoring/alerts.yml`)

## 8. Infra & industrialisation
- [ ] **Terraform** : bucket S3 (Bronze/Silver/Gold), RDS Postgres, IAM, EC2 Spark
- [ ] K8s (si déploiement cloud demandé)
- [ ] CI/CD : build + push images + deploy dev/prod
- [ ] Tests d'intégration (Bronze→Silver→Gold) + performance

---

## Ordre de réalisation recommandé (slices verticales)

> Objectif : une **chaîne complète qui marche** (DVF + INSEE de bout en bout)
> avant d'élargir aux autres sources.

1. **INSEE communes → Bronze** — le référentiel qui débloque les jointures
2. **DVF Bronze → Silver (Spark)** — 1er vrai job : typage / nettoyage / Parquet
3. **Silver → Gold Postgres** — `housing_prices` + `city_metrics` (joint INSEE)
4. **Endpoint `housing` sur Gold** — 1ʳᵉ donnée réelle servie par l'API
5. **Câbler le DAG Airflow** sur la chaîne complète (ingest → silver → gold → cache)
6. **1 page Frontend** consommant l'API → démo bout-en-bout
7. Élargir : autres sources, qualité / gouvernance, CI/CD, Terraform

---

## Décisions d'architecture à trancher

| # | Décision | Recommandation |
|---|----------|----------------|
| 1 | Périmètre couche Gold (5 bases ?) | **Postgres seul** (+ Redis), même avec SeLoger → **DuckDB sur Parquet** si analytique interactif lourd → **ClickHouse** en dernier recours. ES seulement si recherche full-text réelle. _Le volume vit dans Bronze/Silver S3, pas dans Postgres._ |
| 2 | Scraping SeLoger/PAP nécessaire ? | Oui **si** le barème exige du volume « big data » ; sinon DVF + INSEE suffisent |
| 3 | Frontend | **Streamlit** (rapide, Python) sauf si l'UX est notée |
| 4 | Spark requis ? | Over-kill pour quelques Go, mais probablement attendu si « Big Data » dans l'intitulé |

_Dernière mise à jour : 2026-06-05_
