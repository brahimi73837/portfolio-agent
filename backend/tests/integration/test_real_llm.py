"""Real Vertex AI calls — costs a few tokens. Gated so it never runs by accident.

Run deliberately:  RUN_LLM_TESTS=1 .venv/bin/python -m pytest tests/integration -q

Requires: ADC (`gcloud auth application-default login`) and a built FAISS index
(`python scripts/ingest.py`). Keep the number of cases tiny on purpose.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_TESTS") != "1",
    reason="Set RUN_LLM_TESTS=1 to run real-LLM integration tests (uses tokens).",
)


def _answer(question: str) -> str:
    from app.retriever import get_retriever
    from app.chain import generate_answer

    r = get_retriever()
    vec = r.embed_query(question)
    ctx = r.format_context(r.search_by_vector(vec))
    return generate_answer(ctx, [], question)


def test_grounded_answer_mentions_known_fact():
    # The sample KB says Brahim built an AI portfolio chatbot — a real answer should reflect the KB.
    ans = _answer("What has Brahim built?").lower()
    assert any(word in ans for word in ("chatbot", "portfolio", "project"))


def test_off_topic_is_refused():
    ans = _answer("What is the capital of France?").lower()
    # Should decline / steer back to Brahim, not answer "Paris".
    assert "paris" not in ans
    assert "brahim" in ans
