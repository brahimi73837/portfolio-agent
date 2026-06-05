from app.config import get_settings
from app.ratelimit import check_rate_limits, reserve_budget


def test_per_minute_limit_trips():
    s = get_settings()
    ip = "1.2.3.4"
    # First N allowed, the next one blocked.
    for _ in range(s.rate_limit_per_minute):
        assert check_rate_limits(ip).allowed
    blocked = check_rate_limits(ip)
    assert not blocked.allowed
    assert blocked.reason == "per_minute"


def test_different_ips_are_independent():
    for _ in range(get_settings().rate_limit_per_minute):
        check_rate_limits("10.0.0.1")
    # A different IP still gets through.
    assert check_rate_limits("10.0.0.2").allowed


def test_global_budget_circuit_breaker(monkeypatch):
    # Shrink the cap so the test is fast and cheap.
    monkeypatch.setattr(get_settings(), "global_daily_request_cap", 3)
    allowed = [reserve_budget().allowed for _ in range(3)]
    assert all(allowed)
    tripped = reserve_budget()
    assert not tripped.allowed
    assert tripped.reason == "global_day"
