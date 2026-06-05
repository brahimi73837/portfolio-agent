"""Rate limiting + global daily budget — the wallet's bodyguard.

Three independent checks, all backed by Redis counters with TTLs:
  * per-IP per-minute   — stops a single client hammering us.
  * per-IP per-day      — stops slow-drip abuse from one client.
  * global per-day cap   — the circuit breaker: once total daily requests hit the
                           cap, NO paid LLM call is made by anyone until midnight.

If Redis is down we fall back to in-process counters so the budget is still
protected on a single instance (fail closed on cost, not open).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import get_settings
from .redis_client import get_redis

log = logging.getLogger("portfolio.ratelimit")


@dataclass
class LimitDecision:
    allowed: bool
    reason: str | None = None  # "per_minute" | "per_ip_day" | "global_day"


# In-process fallback counters: {key: (count, reset_epoch)}
_fallback: dict[str, tuple[int, float]] = {}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _seconds_until_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(86_400 - (now - tomorrow).total_seconds() % 86_400)


def _incr_with_ttl(key: str, ttl: int) -> int:
    """Increment a counter, setting its TTL on first creation. Redis or fallback."""
    client = get_redis()
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl, nx=True)  # only set TTL when key is new
            count, _ = pipe.execute()
            return int(count)
        except Exception as exc:  # noqa: BLE001
            log.warning("Redis incr failed (%s) — using in-process fallback", exc)

    # Fallback: in-process counter with manual expiry.
    now = time.time()
    count, reset = _fallback.get(key, (0, now + ttl))
    if now >= reset:
        count, reset = 0, now + ttl
    count += 1
    _fallback[key] = (count, reset)
    return count


def check_rate_limits(client_ip: str) -> LimitDecision:
    """Per-IP throttles. Call for EVERY incoming request (cheap, stops spam early).

    These do not consume the paid-generation budget — they just stop one client
    from hammering the service.
    """
    s = get_settings()
    midnight_ttl = _seconds_until_midnight_utc()

    minute = int(time.time() // 60)
    per_min = _incr_with_ttl(f"rl:min:{client_ip}:{minute}", 60)
    if per_min > s.rate_limit_per_minute:
        return LimitDecision(False, "per_minute")

    per_day = _incr_with_ttl(f"rl:day:{client_ip}:{_today()}", midnight_ttl)
    if per_day > s.rate_limit_per_day_per_ip:
        return LimitDecision(False, "per_ip_day")

    return LimitDecision(True)


def reserve_budget() -> LimitDecision:
    """Global daily circuit breaker. Call ONLY right before a paid LLM generation.

    Cached/canned/guarded replies never reach here, so they don't drain the budget.
    Once the cap is hit, no paid call is made by anyone until UTC midnight.
    """
    s = get_settings()
    midnight_ttl = _seconds_until_midnight_utc()
    global_count = _incr_with_ttl(f"budget:global:{_today()}", midnight_ttl)
    if global_count > s.global_daily_request_cap:
        log.warning("Global daily cap hit (%s)", global_count)
        return LimitDecision(False, "global_day")
    return LimitDecision(True)
