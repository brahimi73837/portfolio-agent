"""Single shared Redis connection.

Everything that needs Redis (caching, rate limiting, budget) imports get_redis()
from here so we open exactly one connection pool. If Redis is unreachable we return
None and callers degrade gracefully (see ratelimit.py / cache.py).
"""
from __future__ import annotations

import logging

import redis

from .config import get_settings

log = logging.getLogger("portfolio.redis")

_client: redis.Redis | None = None
_checked = False


def get_redis() -> redis.Redis | None:
    """Return a live Redis client, or None if it can't be reached.

    We ping once and cache the result. decode_responses=True so we work with str.
    """
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    settings = get_settings()
    try:
        client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _client = client
        log.info("Connected to Redis at %s", settings.redis_url.split("@")[-1])
    except Exception as exc:  # noqa: BLE001 - any failure means "no redis"
        log.warning("Redis unavailable (%s) — caching/limits degrade gracefully", exc)
        _client = None
    return _client


def reset_redis_cache() -> None:
    """Test helper: force re-evaluation of the connection."""
    global _client, _checked
    _client, _checked = None, False
