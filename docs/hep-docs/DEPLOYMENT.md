# HOMEPEDIA — Déploiement (DevOps)

Déploiement **hybride VPS + GCP** : un **VPS OVH** always-on (service + orchestration
Airflow) et une **VM GCP Compute Engine** allumée **à la demande** par Airflow pour
le calcul Spark, plus **S3 (AWS)** comme object store Bronze/Silver.

```
   sources ──► Airflow (VPS) ──ingest──► S3 (AWS): bronze / silver
                    │
                    │ 1. ComputeEngineStartInstanceOperator (ADC)
                    │ 2. SSH  spark-submit --master local[*]   (OS Login + clé)
                    │ 3. ComputeEngineStopInstanceOperator
                    ▼
   ┌──────── GCP VM (on-demand) ────────┐        ┌──────────── OVH VPS (always-on) ───────────┐
   │  Spark (container homepedia-        │        │  Caddy (TLS) ─► frontend / api / airflow-ui │
   │  spark-master, local[*])            │──JDBC─►│  PostgreSQL (Gold) · Redis · Airflow        │
   │  IP statique 35.254.120.223         │  5432  │  (webserver + scheduler + metadata Postgres)│
   └─────────────────────────────────────┘        └─────────────────────────────────────────────┘
```

- **VPS** : `iac/docker/prod/vps/docker-compose.yml` — Caddy, API, frontend, Redis,
  PostgreSQL (Gold), Airflow (webserver + scheduler + metadata Postgres).
- **VM GCP** : `iac/docker/prod/gcp-vm/docker-compose.yml` — un seul conteneur Spark
  (`local[*]`), `restart: always` (revient à chaque boot). Écrit le Gold dans le
  Postgres du VPS via JDBC (port 5432).
- Airflow (LocalExecutor) orchestre : il **démarre** la VM, y **soumet** les jobs
  Spark par **SSH**, puis l'**éteint** (même en cas d'échec → économie).

## Pourquoi ce montage (contraintes du compte Epitech)

- L'**AWS EC2** a été abandonné : le compte étudiant n'a pas `ec2:Start/StopInstances`.
- Sur **GCP**, l'utilisateur est **Owner** du projet → start/stop OK. Mais deux org
  policies contraignent l'auth non-interactive d'Airflow :
  - **Clés de SA interdites** (`iam.disableServiceAccountKeyCreation`) → on utilise
    l'**ADC utilisateur** (`gcloud auth application-default login` → `adc.json`,
    type `authorized_user`), monté dans Airflow via `GOOGLE_APPLICATION_CREDENTIALS`.
  - **OS Login activé** → l'accès SSH passe par un user POSIX (`semakia_djaba_epitech_eu`)
    et une clé enregistrée dans OS Login (`gcloud compute os-login ssh-keys add`), pas
    par les métadonnées `ssh-keys`.
- L'IP externe change à chaque start → on a réservé une **IP statique** (`35.254.120.223`).

---

## 1. Images & CI/CD

Quatre images de prod (`iac/docker/prod/<name>/Dockerfile`) : **api**, **frontend**,
**spark**, **airflow**, poussées sur **GHCR** par `.github/workflows/deploy.yml`.

- **`ci.yml`** (PR/push) : ruff + `pytest tests/unit` ; front lint + `tsc` + build.
- **`deploy.yml`** (tag `v*` / manuel) : build+push des 4 images, puis déploiement
  SSH du **VPS** (`pull` + `up -d`). La VM GCP, souvent éteinte, se met à jour toute
  seule : un *startup-script* fait `docker compose pull && up -d` à chaque boot.

### Secrets / variables GitHub (repo → Settings → Secrets and variables → Actions)

| Nom | Type | Rôle |
|---|---|---|
| `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_DEPLOY_PATH` | secret | SSH déploiement VPS (SSH_KEY = clé **privée** ; DEPLOY_PATH = **racine du repo cloné** sur le VPS) |
| `ENV_PROD_B64` | secret | le `.env.prod` **racine rempli**, encodé base64 (`base64 -w0 .env.prod`) |
| `GCP_ADC_B64` | secret | `adc.json` (ADC GCP) encodé base64 |
| `SPARK_VM_KEY_B64` | secret | clé SSH privée de la VM Spark (`airflow_spark_vm`) encodée base64 |
| `NEXT_PUBLIC_API_URL` | variable | URL API inlinée au build du front |

`GITHUB_TOKEN` (fourni) pousse sur GHCR. Le job `deploy-vps` **décode ces 3 secrets
base64** sur le VPS (`.env.prod`, `secrets/adc.json`, `secrets/spark_vm`, en `0600`)
puis fait `pull` + `up -d` — plus aucun dépôt manuel de fichier. Le pilotage GCP se
fait **depuis Airflow** (ADC + clé SSH montées), pas via des secrets GitHub côté GCP.

> Pour (re)générer un secret base64 : `base64 -w0 <fichier>` et coller la ligne dans
> *Settings → Secrets and variables → Actions*. Refaire pour `ENV_PROD_B64` à chaque
> changement de `.env.prod`.

---

## 2. Un seul `.env.prod` (racine) + les secrets

Toute la prod lit **un unique `.env.prod` à la racine du repo** (les deux compose y
pointent en relatif : `env_file: ../../../../.env.prod`). Sur le VPS, le repo cloné
ressemble à :

```
<racine repo>/
├─ .env.prod                       (généré par la CI depuis ENV_PROD_B64)
└─ iac/docker/prod/vps/
   ├─ docker-compose.yml           (versionné)
   └─ secrets/
      ├─ adc.json                  (depuis GCP_ADC_B64 — ADC gcloud application-default)
      └─ spark_vm                  (depuis SPARK_VM_KEY_B64 — clé SSH privée OS Login)
```

Ces trois fichiers sont **écrits automatiquement par `deploy.yml`** (décodage base64,
`0600`) à chaque déploiement, puis montés en lecture seule dans les conteneurs Airflow.
Tu n'as à les déposer à la main **que** pour un `up` manuel hors CI (§5). La **VM GCP**
utilise le *même* `.env.prod` racine (repo cloné dessus aussi — cf. §3). `.env.prod`,
`secrets/` et `*adc*.json` sont gitignorés ; seul `.env.prod.example` (racine) est versionné.

---

## 3. Provisionnement de la VM GCP (une fois)

Depuis Cloud Shell / ton poste (compte Owner) — l'IP statique, l'ADC, la clé SSH
OS Login et l'ouverture SSH sont déjà en place. Il reste **Docker + Spark** sur la VM :

```bash
gcloud compute ssh instance-20260704-224836 --zone us-central1-c --command='
  set -e
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker $(whoami)
  sudo systemctl enable --now docker
'
# cloner le repo sur la VM + y déposer le MÊME .env.prod racine, puis :
gcloud compute ssh instance-20260704-224836 --zone us-central1-c --command='
  cd ~/T-DAT-902-PAR_5              # racine du repo cloné (contient .env.prod)
  docker login ghcr.io             # PAT read:packages
  ./iac/scripts/deploy.sh gcp-vm latest
'
```

Pour que la VM tourne toujours `:latest` à chaque réveil, ajouter un startup-script
(lance le compose Spark depuis la racine du repo, avec le `.env.prod` racine) :

```bash
gcloud compute instances add-metadata instance-20260704-224836 --zone us-central1-c \
  --metadata=startup-script='#!/bin/bash
cd /home/'"$USER"'/T-DAT-902-PAR_5 && \
docker compose -f iac/docker/prod/gcp-vm/docker-compose.yml --env-file .env.prod pull && \
docker compose -f iac/docker/prod/gcp-vm/docker-compose.yml --env-file .env.prod up -d'
```

---

## 4. Pare-feu

- **VPS** : ouvrir **80/443** au public. Ouvrir **5432 uniquement depuis
  `35.254.120.223`** (écriture Gold par Spark). Airflow UI reste sur `127.0.0.1`.
- **GCP** : autoriser **tcp:22** entrant (au moins depuis l'IP du VPS `91.134.132.149`)
  pour que le SSHOperator atteigne la VM. Le start/stop passe par l'API Compute (ADC),
  pas par le réseau.

---

## 5. Mise en route — VPS

**Via la CI (nominal)** : pousser un tag `v*` (ou lancer `deploy.yml` manuellement).
Le job écrit le `.env.prod` racine + `iac/docker/prod/vps/secrets/` depuis les secrets
base64 puis `pull` + `up -d`. Rien à faire à la main, hormis avoir cloné le repo dans
`VPS_DEPLOY_PATH` (= racine du repo sur le VPS).

**Premier `up` manuel (optionnel, hors CI)** — depuis la **racine du repo** :

```bash
cd <VPS_DEPLOY_PATH>          # racine du repo cloné
cp .env.prod.example .env.prod && $EDITOR .env.prod
#   Domaines, mots de passe, AUTH_SECRET (openssl rand -base64 33),
#   AWS_* + S3_*, AIRFLOW_FERNET_KEY, GCP_* + SPARK_SSH_* (déjà pré-remplis).
#   1er boot : SEED_ON_START=1 (admin démo du front), puis repasser à 0.
mkdir -p iac/docker/prod/vps/secrets
cp /chemin/adc.json          iac/docker/prod/vps/secrets/adc.json
cp /chemin/airflow_spark_vm  iac/docker/prod/vps/secrets/spark_vm
chmod 600 .env.prod iac/docker/prod/vps/secrets/*

./iac/scripts/deploy.sh vps <IMAGE_TAG>              # pull + up -d
```

> Après avoir rempli `.env.prod` en manuel, régénère `ENV_PROD_B64`
> (`base64 -w0 .env.prod`) pour que les déploiements CI suivants restent alignés.

Vérifs :

```bash
curl -fsS https://$API_DOMAIN/health           # {"status":"ok"}
curl -fsS https://$API_DOMAIN/ready            # postgres/redis/s3
```

### Lancer les pipelines

UI Airflow : `https://$AIRFLOW_DOMAIN` (si exposé) ou `ssh -L 8080:localhost:8080 <vps>`.
Déclencher `housing`, `mobility_etl`, `amenities_etl` (ou `airflow dags trigger`).
Chaque run **démarre la VM GCP**, attend que le conteneur Spark réponde, lance les
`spark-submit` par SSH, puis **éteint la VM** (`stop_spark_vm`, `trigger_rule=all_done`).
En dev (pas de `SPARK_SSH_CONN_ID`), les mêmes DAGs tournent en local (`docker exec`),
`start/stop/wait` étant des no-ops.

---

## 6. Flux courant, rollback, exploitation

- **Déploiement** : tag `v1.2.3` → `deploy.yml` build+push + déploie le VPS. La VM se
  met à jour au prochain start (startup-script).
- **Rollback** VPS : depuis la racine du repo, `./iac/scripts/deploy.sh vps v1.2.2`.
  Les volumes (Postgres Gold, SQLite auth, metadata Airflow) persistent.
- **Santé** : `docker compose ps`, `GET /health` & `/ready` (API), `/health` (Airflow).
- **Logs** : `docker compose logs -f <service>` (rotation json-file 10m×5).
- **Coût GCP** : la VM ne tourne que pendant les DAGs ; vérifier qu'aucun run bloqué
  ne la laisse allumée (le `stop_spark_vm` en `all_done` couvre les échecs).

## 7. Checklist secrets (ne jamais committer)

- `.env.prod` racine (VPS **et** VM GCP) : `POSTGRES_PASSWORD`, `AUTH_SECRET`, `AWS_*`,
  `AIRFLOW_FERNET_KEY`, `AIRFLOW_ADMIN_PASSWORD`, `GCP_*`, `SPARK_SSH_*`.
- VPS `iac/docker/prod/vps/secrets/` : `adc.json` (ADC GCP) + `spark_vm` (clé SSH privée).
- GitHub : `VPS_*` (clé SSH déploiement), `ENV_PROD_B64`, `GCP_ADC_B64`,
  `SPARK_VM_KEY_B64`, + var `NEXT_PUBLIC_API_URL`.

`.env.prod`, `secrets/` et `*adc*.json` sont gitignorés ; seul `.env.prod.example`
(racine) est versionné.
