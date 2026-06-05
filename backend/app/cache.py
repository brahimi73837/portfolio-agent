"""Response cache — the token-bill saver.

Two layers, both in Redis, both namespaced by the knowledge-base version so a
re-ingest automatically invalidates stale answers (FR-018):

  L1 exact   : normalized question -> answer. O(1) GET. Catches identical questions.
  L2 semantic: near-duplicate questions reuse an answer via cosine similarity on the
               question embedding. We reuse the SAME embedding computed for retrieval,
               so a semantic-cache lookup costs zero extra API calls.

If Redis is down, every function no-ops gracefully (cache simply "misses").
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import numpy as np

from .config import get_settings
from .redis_client import get_redis

log = logging.getLogger("portfolio.cache")

_SEMANTIC_MAX_ENTRIES = 500  # bound memory on the cheap VM


def get_kb_version() -> str:
    """Read the KB version stamped by the ingest script (defaults to '0')."""
    vfile = get_settings().faiss_path / "kb_version.txt"
    try:
        return vfile.read_text().strip() or "0"
    except OSError:
        return "0"


def _normalize(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def _exact_key(question: str) -> str:
    h = hashlib.sha256(_normalize(question).encode()).hexdigest()[:32]
    return f"resp:{get_kb_version()}:{h}"


def _semantic_key() -> str:
    return f"sem:{get_kb_version()}"


# ---------------- L1 exact ----------------

def exact_get(question: str) -> str | None:
    client = get_redis()
    if client is None:
        return None
    try:
        return client.get(_exact_key(question))
    except Exception as exc:  # noqa: BLE001
        log.warning("exact_get failed: %s", exc)
        return None


def exact_set(question: str, answer: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.set(_exact_key(question), answer, ex=get_settings().response_cache_ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        log.warning("exact_set failed: %s", exc)


# ---------------- L2 semantic ----------------

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)


def semantic_get(query_vec: list[float]) -> str | None:
    """Return a cached answer whose question is ~similar to this one, else None."""
    s = get_settings()
    if not s.semantic_cache_enabled:
        return None
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.lrange(_semantic_key(), 0, -1)
    except Exception as exc:  # noqa: BLE001
        log.warning("semantic_get failed: %s", exc)
        return None
    if not raw:
        return None

    q = np.asarray(query_vec, dtype=np.float32)
    best_sim, best_answer = -1.0, None
    for item in raw:
        try:
            entry = json.loads(item)
            sim = _cosine(q, np.asarray(entry["vec"], dtype=np.float32))
            if sim > best_sim:
                best_sim, best_answer = sim, entry["answer"]
        except (json.JSONDecodeError, KeyError):
            continue

    if best_answer is not None and best_sim >= s.semantic_cache_threshold:
        log.info("semantic cache HIT (sim=%.3f)", best_sim)
        return best_answer
    return None


def semantic_set(query_vec: list[float], answer: str) -> None:
    s = get_settings()
    if not s.semantic_cache_enabled:
        return
    client = get_redis()
    if client is None:
        return
    entry = json.dumps({"vec": [round(float(x), 5) for x in query_vec], "answer": answer})
    try:
        pipe = client.pipeline()
        pipe.lpush(_semantic_key(), entry)
        pipe.ltrim(_semantic_key(), 0, _SEMANTIC_MAX_ENTRIES - 1)  # keep most-recent N
        pipe.expire(_semantic_key(), s.response_cache_ttl_seconds)
        pipe.execute()
    except Exception as exc:  # noqa: BLE001
        log.warning("semantic_set failed: %s", exc)
