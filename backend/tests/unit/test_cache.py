import numpy as np

from app import cache


def test_normalize_collapses_whitespace_and_case():
    assert cache._normalize("  What   IS  this?  ") == "what is this?"


def test_cosine_identity_and_orthogonal():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert cache._cosine(a, b) == 1.0
    assert abs(cache._cosine(a, c)) < 1e-6


def test_cache_noops_without_redis():
    # no_redis fixture is active -> these must not raise and must "miss".
    assert cache.exact_get("anything") is None
    cache.exact_set("q", "a")  # no-op, no exception
    assert cache.semantic_get([0.1, 0.2, 0.3]) is None
    cache.semantic_set([0.1, 0.2, 0.3], "a")  # no-op


def test_kb_version_defaults_to_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(cache.get_settings(), "faiss_dir", str(tmp_path))
    assert cache.get_kb_version() == "0"
