"""Shared infrastructure clients (DB engine, Redis, S3).

Lazily constructed singletons reused across requests. Each `ping_*` helper is
used by the readiness probe and returns (ok, detail) without raising, so a
single dead dependency degrades the health report rather than the whole API.
"""

from __future__ import annotations

from functools import lru_cache

import boto3
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.api.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    # pool_pre_ping avoids handing out connections dropped by Postgres.
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5)


@lru_cache
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def ping_postgres() -> tuple[bool, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:  # noqa: BLE001 - report, don't crash the probe
        return False, str(exc)


def ping_redis() -> tuple[bool, str]:
    try:
        get_redis().ping()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def ping_s3() -> tuple[bool, str]:
    try:
        get_s3_client().list_buckets()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
