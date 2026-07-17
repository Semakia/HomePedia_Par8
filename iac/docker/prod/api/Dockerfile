# HOMEPEDIA — FastAPI backend (PROD image).
# Multi-stage: install deps into an isolated prefix, then copy into a slim,
# non-root runtime. No --reload; served by uvicorn workers (stateless — the
# bulk-map cache lives in Redis, so multiple workers are safe). Built from the
# repo root (context = repo root).
#
#   docker build -f iac/docker/prod/api/Dockerfile -t homepedia/api:<tag> .

# --- Stage 1: build the dependency tree -------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# psycopg2-binary ships wheels, so no compiler/libpq-dev needed.
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements/base.txt

# --- Stage 2: slim runtime --------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY --from=builder /install /usr/local
COPY src ./src

USER appuser
EXPOSE 8000

# Liveness probe against the app's own /health route.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"]

# WEB_CONCURRENCY tunes the worker count (default 4). Proxied by Caddy/Traefik,
# which terminate TLS — uvicorn stays plain HTTP behind it.
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-4} --proxy-headers --forwarded-allow-ips '*'"]
