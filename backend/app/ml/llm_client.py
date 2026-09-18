"""Optional LLM-backed phrasing for the AI Copilot — closes the "Copilot: template
engine -> LLM-backed synthesis" gap in docs/architecture.md §10.

The facts always come from the database (copilot_service.py's intent handlers);
this module is only ever asked to phrase an already-computed set of facts into a
sentence, never to answer a question on its own. If no API key is configured, or
the call fails for any reason, callers fall back to the deterministic template —
the platform must work identically with zero external dependencies.
"""
from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger("llm_copilot")

_PROMPT_TEMPLATE = """You are a business analytics assistant. A manager asked: "{question}"

Here are the ONLY facts you may use to answer, already computed from their real data:
{facts}

Write a single, natural-language paragraph (2-4 sentences) answering the question using
ONLY the facts above. Do not invent any number, name, or detail not listed above. If the
facts are insufficient to answer, say so plainly rather than guessing."""


def generate_llm_answer(question: str, facts: dict) -> str | None:
    """Returns a phrased answer, or None if no key is configured or the call failed
    (in which case the caller should fall back to its template answer)."""
    settings = get_settings()
    if not settings.llm_api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.llm_api_key)
        prompt = _PROMPT_TEMPLATE.format(question=question, facts=facts)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text")).strip()
        return text or None
    except Exception:  # noqa: BLE001 - any failure here must silently fall back, never break the Copilot
        logger.exception("LLM Copilot call failed; falling back to template answer")
        return None
