#!/bin/bash
# =============================================================================
# HOMEPEDIA — startup-script de la VM Spark (GCP)
# -----------------------------------------------------------------------------
# GCP exécute ce script (en root) à CHAQUE démarrage de l'instance. Comme
# Airflow (sur le VPS) démarre la VM juste avant chaque pipeline, on en profite
# pour re-puller la dernière image `homepedia-spark:latest` et relancer le
# conteneur — la VM tourne donc toujours le code Spark à jour, sans intervention.
#
# `restart: always` a déjà relancé le conteneur depuis l'image en cache dès que
# le démon Docker est prêt ; ce script ne fait que le mettre à jour si une image
# plus récente existe. Un échec de pull (réseau, GHCR indispo) est non fatal :
# le conteneur en cache continue de tourner.
#
# Auth GHCR : on réutilise le `docker login` déjà stocké dans le ~/.docker de
# l'utilisateur (DOCKER_CONFIG), donc pas de secret à passer ici.
#
# Attacher / mettre à jour ce script sur l'instance (depuis Cloud Shell) :
#   gcloud compute instances add-metadata instance-20260704-224836 \
#     --zone us-central1-c \
#     --metadata-from-file startup-script=iac/docker/prod/gcp-vm/startup.sh
# =============================================================================
set -u

VM_USER="semakia_djaba_epitech_eu"
HOME_DIR="/home/${VM_USER}"
APP_DIR="${HOME_DIR}/homepedia"
export DOCKER_CONFIG="${HOME_DIR}/.docker"   # réutilise le login GHCR de l'user

cd "${APP_DIR}" || { echo "startup: ${APP_DIR} introuvable"; exit 0; }

# Attendre que le démon Docker soit prêt (jusqu'à ~30 s).
for _ in $(seq 1 15); do
  docker info >/dev/null 2>&1 && break
  sleep 2
done

# Mise à jour best-effort : un échec ne doit pas empêcher le conteneur en cache.
docker compose --env-file .env.prod pull  || echo "startup: pull échoué (on garde l'image en cache)"
docker compose --env-file .env.prod up -d || echo "startup: up échoué"

echo "startup: terminé"
