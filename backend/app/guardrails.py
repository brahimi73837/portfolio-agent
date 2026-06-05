"""Input guardrails — the cheap, deterministic first line of defence.

Order of concerns (cheapest first):
  1. Empty input            -> friendly nudge, no LLM call.
  2. Oversized input        -> truncate to a hard char cap (cost control).
  3. Prompt injection /      -> high-precision regex; obvious attacks get a canned
     jailbreak attempts          reply WITHOUT ever reaching the model.

Off-topic and sensitive questions are NOT keyword-filtered here (keyword filters
produce annoying false positives on legitimate questions). Those are enforced by
the strict system prompt in prompts.py and verified by tests — the model is cheap
and far better at nuance than a regex.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .config import get_settings
from .prompts import EMPTY_INPUT_REPLY, INJECTION_REPLY


class GuardAction(str, Enum):
    ANSWER = "answer"        # safe to proceed to retrieval + generation
    EMPTY = "empty"          # nothing to answer
    INJECTION = "injection"  # blocked, return canned reply


@dataclass
class GuardResult:
    action: GuardAction
    text: str                 # cleaned (possibly truncated) user text
    canned_reply: str | None  # set when action != ANSWER


# High-precision patterns. We want very few false positives: each pattern targets
# language that is essentially only used to attack a system prompt.
_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+|the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:instruction|prompt|message|rule)",
    r"disregard\s+(?:all\s+|the\s+|your\s+)?(?:previous|prior|above)\s+(?:instruction|prompt|rule)",
    r"forget\s+(?:all\s+|your\s+|the\s+)?(?:previous\s+|above\s+)?(?:instruction|prompt|rule)",
    r"(?:reveal|show|print|repeat|tell\s+me|what\s+is|what's|expose|leak)\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+prompt|system\s+message|instructions|prompt|rules|guidelines)",
    r"system\s+prompt",
    r"developer\s+mode",
    r"\bDAN\b|do\s+anything\s+now",
    r"jailbreak",
    r"you\s+are\s+now\s+(?:a|an|the)\b",
    r"(?:act|behave|respond)\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:a\s+|an\s+)?(?:different|unrestricted|uncensored)",
    r"pretend\s+(?:to\s+be|you\s+are)\b",
    r"(?:override|bypass|disable)\s+(?:your\s+)?(?:safety|guardrail|filter|restriction|rule|instruction)",
    r"new\s+(?:instructions?|rules?)\s*:\s*",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))


def check_input(text: str) -> GuardResult:
    """Run the deterministic input guards. Pure function — trivially unit-testable."""
    settings = get_settings()
    cleaned = (text or "").strip()

    if not cleaned:
        return GuardResult(GuardAction.EMPTY, "", EMPTY_INPUT_REPLY)

    # Cost control: never let a giant paste become a giant (paid) prompt.
    if len(cleaned) > settings.max_input_chars:
        cleaned = cleaned[: settings.max_input_chars]

    if looks_like_injection(cleaned):
        return GuardResult(GuardAction.INJECTION, cleaned, INJECTION_REPLY)

    return GuardResult(GuardAction.ANSWER, cleaned, None)
