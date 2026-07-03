# HOMEPEDIA

Plateforme data d'analyse de l'immobilier français (prix, transport, emploi, INSEE)
construite sur une **architecture médaillon** (Bronze → Silver → Gold) orchestrée
par Airflow.

> Projet Epitech **T-DAT-902**. Architecture détaillée : [docs/README.md](docs/README.md)
> · diagramme : [docs/data_flow_archi.png](docs/data_flow_archi.png).

## Stack (socle dev)

| Couche | Techno | Port local |
|---|---|---|
| Object store (Bronze/Silver/Gold) | MinIO (S3) | 9000 / 9001 (console) |
| Gold relationnel + métadonnées Airflow | PostgreSQL 16 | 5432 |
| Cache | Redis 7 | 6379 |
| Moteur ETL Silver | Spark 3.5 (master + worker) | 7077 / 8090 (UI) |
| API | FastAPI | 8000 |
| Orchestration | Airflow 2.10 (LocalExecutor) | 8080 |

## Prérequis

- Docker + Docker Compose
- [Task](https://taskfile.dev) (`task --version`) — facultatif mais recommandé
- Python 3.12 (pour lancer les tests/lint hors conteneur)

## Démarrage rapide

```bash
# 1. Créer le .env à partir du template
task init           # ou : cp .env.dist .env

# 2. Démarrer le data plane (build + up)
task up

# 3. (optionnel) Démarrer Airflow une fois le data plane up
task airflow:up
```

Points d'entrée :
- API + Swagger : http://localhost:8000/docs
- Santé : http://localhost:8000/health · Readiness : http://localhost:8000/ready
- MinIO console : http://localhost:9001 (`minioadmin` / `minioadmin`)
- Spark master UI : http://localhost:8090
- Airflow : http://localhost:8080 (`admin` / `admin`)

### Sans Task (docker compose brut)

```bash
# `.env` est chargé automatiquement depuis le répertoire courant (racine du repo)
docker compose -f iac/docker/dev/docker-compose.yml up -d --build
docker compose -f iac/docker/dev/airflow/docker-compose.yml up -d
```

## Commandes utiles

```bash
task            # liste toutes les commandes
task ps         # services en cours
task logs -- api   # logs d'un service
task config     # valide la config compose (dev + airflow)
task down       # stop (conserve les volumes)
task nuke       # stop + suppression des volumes (état neuf)
task test       # pytest
task lint       # ruff
task fmt        # black + ruff --fix
```

## Structure

```
iac/docker/dev/        # stack docker compose locale (+ Dockerfiles api/spark)
iac/scripts/           # bootstrap (buckets S3, init DB Airflow)
requirements/          # dépendances (base / dev / spark / airflow)
src/api/               # FastAPI (config, dependencies, routers)
src/data_ingestion/    # connecteurs sources -> Bronze
src/data_processing/   # ETL Spark Bronze -> Silver, qualité, agrégations
src/analytics/         # couche Gold (schémas SQL, pipelines)
airflow/dags/          # DAGs (homepedia_etl = pipeline principal)
```

## État d'avancement

- [x] **Socle exécutable** : infra dev, API `/health`+`/ready`, DAG smoke
- [ ] Vertical slice : 1 source → Bronze → Silver → Gold → endpoint
- [ ] Extension aux autres sources
- [ ] Gouvernance (lineage, qualité, RBAC)
