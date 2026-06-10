"""FastAPI app — the request pipeline.

POST /chat runs, in order (cheapest/safest first):
  1. per-IP rate limit        (Redis)        -> friendly throttle, no LLM call
  2. input guard              (deterministic) -> empty / injection canned replies
  3. L1 exact cache           (Redis)        -> instant, no LLM call
  4. embed query once         (Vertex)        -> reused for cache + retrieval
  5. L2 semantic cache        (Redis)        -> near-duplicate hit, no LLM call
  6. global daily budget      (Redis)        -> circuit breaker before paid call
  7. retrieve top-k + generate (FAISS+Gemini)
  8. store answer in caches

GET /health reports KB + Redis readiness.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import cache, prompts
from .chain import generate_answer
from .config import get_settings
from .guardrails import GuardAction, check_input
from .ratelimit import check_rate_limits, reserve_budget
from .redis_client import get_redis
from .retriever import faiss_exists, get_retriever

logging.basicConfig(level=get_settings().log_level)
log = logging.getLogger("portfolio.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the KB and wire LangChain's native Redis LLM cache at startup."""
    s = get_settings()
    if faiss_exists():
        try:
            get_retriever()  # load FAISS once
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to load retriever: %s", exc)
    else:
        log.warning("FAISS index missing — run scripts/ingest.py. /chat will return NOT_READY.")

    # LangChain best practice: a native LLM cache so identical prompts skip the model.
    redis_conn = get_redis()
    if redis_conn is not None:
        try:
            from langchain_community.cache import RedisCache
            from langchain_core.globals import set_llm_cache

            set_llm_cache(RedisCache(redis_conn, ttl=s.response_cache_ttl_seconds))
            log.info("LangChain RedisCache enabled")
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not enable LangChain RedisCache: %s", exc)
    yield


app = FastAPI(title="Brahim Portfolio Chatbot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's question")
    history: list[Turn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    cached: bool = False
    source: str = "model"  # model | cache_exact | cache_semantic | guard | limit | budget | error


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Cloud Run sets X-Forwarded-For; take the first hop."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _retrieval_query(message: str, history: list[Turn]) -> str:
    """Prepend the previous user turn so follow-ups ('tell me more') retrieve well."""
    prev_user = next((t.content for t in reversed(history) if t.role == "user"), "")
    return f"{prev_user} {message}".strip() if prev_user else message


@app.get("/health")
def health():
    redis_ok = get_redis() is not None
    return {
        "status": "ok" if faiss_exists() else "degraded",
        "kb_ready": faiss_exists(),
        "redis_ok": redis_ok,
        "kb_version": cache.get_kb_version(),
        "model": get_settings().gemini_model,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    ip = _client_ip(request)

    # 1) per-IP rate limit (applies to everything)
    rl = check_rate_limits(ip)
    if not rl.allowed:
        return ChatResponse(reply=prompts.RATE_LIMITED_REPLY, source="limit")

    # 2) deterministic input guard
    guard = check_input(req.message)
    if guard.action is not GuardAction.ANSWER:
        return ChatResponse(reply=guard.canned_reply or prompts.OFF_TOPIC_REPLY, source="guard")
    question = guard.text

    # KB must be ready to answer anything grounded.
    if not faiss_exists():
        return ChatResponse(reply=prompts.NOT_READY_REPLY, source="error")

    # 3) L1 exact cache
    hit = cache.exact_get(question)
    if hit is not None:
        return ChatResponse(reply=hit, cached=True, source="cache_exact")

    # 4) embed the query ONCE (reused by semantic cache + retrieval)
    history = [t.model_dump() for t in req.history]
    try:
        retriever = get_retriever()
        query_vec = retriever.embed_query(_retrieval_query(question, req.history))
    except Exception as exc:  # noqa: BLE001
        log.error("embedding/retriever error: %s", exc)
        return ChatResponse(reply=prompts.LLM_ERROR_REPLY, source="error")

    # 5) L2 semantic cache
    sem = cache.semantic_get(query_vec)
    if sem is not None:
        return ChatResponse(reply=sem, cached=True, source="cache_semantic")

    # 6) global daily budget — only paid generations reach here
    if not reserve_budget().allowed:
        return ChatResponse(reply=prompts.BUDGET_EXCEEDED_REPLY, source="budget")

    # 7) retrieve + generate
    try:
        docs = retriever.search_by_vector(query_vec)
        context = retriever.format_context(docs)
        gen = generate_answer(context, history, question)
    except Exception as exc:  # noqa: BLE001
        log.error("generation error: %s", exc)
        return ChatResponse(reply=prompts.LLM_ERROR_REPLY, source="error")

    # 8) populate caches for next time — but never cache a cut-off answer.
    if not gen.truncated:
        cache.exact_set(question, gen.text)
        cache.semantic_set(query_vec, gen.text)
    return ChatResponse(reply=gen.text, source="model")
