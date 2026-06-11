"""HOMEPEDIA FastAPI application entrypoint.

Minimal but runnable: liveness/readiness probes wired to the real infra clients,
CORS, and the versioned router tree. Business endpoints live under src/api/routers/.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_settings
from src.api.dependencies import ping_postgres, ping_redis, ping_s3
from src.api.routers import cities, housing

settings = get_settings()

app = FastAPI(
    title="HOMEPEDIA API",
    version="0.1.0",
    description="Query layer over the HOMEPEDIA Gold datasets.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
def health() -> dict:
    """Liveness probe: process is up and serving."""
    return {"status": "ok", "service": "homepedia-api", "env": settings.environment}


@app.get("/ready", tags=["ops"])
def ready() -> dict:
    """Readiness probe: report connectivity to each backing service."""
    checks = {
        "postgres": ping_postgres(),
        "redis": ping_redis(),
        "s3": ping_s3(),
    }
    components = {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks.items()}
    all_ok = all(ok for ok, _ in checks.values())
    return {"status": "ready" if all_ok else "degraded", "components": components}


# --- Versioned API surface ---
app.include_router(cities.router, prefix="/api/v1")
app.include_router(housing.router, prefix="/api/v1")
