"""Shared test fixtures. All of these keep tests offline and free (no LLM, no Redis)."""
import pytest

from app import ratelimit
from app import redis_client


@pytest.fixture(autouse=True)
def no_redis(monkeypatch):
    """Force get_redis() to return None so every Redis-backed feature uses its
    graceful fallback path. Keeps unit tests hermetic."""
    redis_client._client = None
    redis_client._checked = True
    yield
    redis_client.reset_redis_cache()


@pytest.fixture(autouse=True)
def clear_fallback_counters():
    """Reset in-process rate-limit counters between tests."""
    ratelimit._fallback.clear()
    yield
    ratelimit._fallback.clear()
