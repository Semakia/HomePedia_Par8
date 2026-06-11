"""Lightweight retry with exponential backoff + jitter.

No external dependency (keeps the ingestion image slim). Wrap any flaky I/O
(HTTP fetch, S3 put) with `@retry(...)`. Retries only the listed exception
types; everything else propagates immediately.
"""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import TypeVar

from src.data_ingestion.utils.logging_utils import get_logger

T = TypeVar("T")
log = get_logger(__name__)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry on `exceptions` with exponential backoff.

    delay = min(max_delay, base_delay * backoff**(attempt-1)) + random jitter.
    Re-raises the last exception once attempts are exhausted.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while True:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt >= max_attempts:
                        log.error(
                            "retry.exhausted",
                            func=func.__name__,
                            attempts=attempt,
                            error=str(exc),
                        )
                        raise
                    delay = min(max_delay, base_delay * backoff ** (attempt - 1))
                    delay += random.uniform(0, jitter * delay)
                    log.warning(
                        "retry.attempt",
                        func=func.__name__,
                        attempt=attempt,
                        next_delay_s=round(delay, 2),
                        error=str(exc),
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
