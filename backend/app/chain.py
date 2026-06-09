"""LangChain orchestration: prompt -> Gemini 2.5 Flash -> text.

This is the LCEL chain at the heart of the app. It assembles a chat prompt from
the system instructions, the retrieved knowledge-base context, the recent
conversation, and the user's question, then runs it through ChatVertexAI and
parses the output to a plain string.
"""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from .config import get_settings
from .prompts import SYSTEM_PROMPT, TRUNCATION_NOTE

log = logging.getLogger("portfolio.chain")

_llm: ChatVertexAI | None = None


def get_llm() -> ChatVertexAI:
    """Singleton chat model. thinking_budget=0 keeps 2.5-flash fast + cheap for short answers."""
    global _llm
    if _llm is None:
        s = get_settings()
        kwargs = dict(
            model=s.gemini_model,
            project=s.gcp_project_id,
            location=s.gcp_location,
            temperature=s.temperature,
            max_output_tokens=s.max_output_tokens,
        )
        try:
            _llm = ChatVertexAI(thinking_budget=s.thinking_budget, **kwargs)
        except TypeError:
            # Older lib without thinking_budget support — degrade gracefully.
            log.warning("ChatVertexAI has no thinking_budget param; continuing without it")
            _llm = ChatVertexAI(**kwargs)
    return _llm


def _build_messages(context: str, history: list[dict], question: str) -> list:
    """Compose the message list: system+context, prior turns, then the question."""
    system = SYSTEM_PROMPT + f"\n\n=== CONTEXT (everything you know about Brahim) ===\n{context}\n=== END CONTEXT ==="
    messages: list = [SystemMessage(content=system)]
    for turn in history[-6:]:  # last 3 exchanges of short-term memory
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai", "bot"):
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=question))
    return messages


def generate_answer(context: str, history: list[dict], question: str) -> str:
    """Run the chain and return the assistant's reply text.

    We invoke the model directly (instead of piping through StrOutputParser) so we
    can read the finish reason: if Gemini hit the max-output-token cap, the answer
    was cut off, and we append a clear note. A LangChain Redis LLM cache (see
    main.py) still serves identical prompts automatically.
    """
    messages = _build_messages(context, history, question)
    response = get_llm().invoke(messages)
    text = (response.content or "").strip()

    finish = str(response.response_metadata.get("finish_reason", "")).upper()
    if "MAX_TOKEN" in finish or "LENGTH" in finish:
        text = (text + TRUNCATION_NOTE) if text else TRUNCATION_NOTE.strip()
    return text
