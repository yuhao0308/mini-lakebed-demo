"""
Tests for Ollama fallback behavior across demo intents.
"""

import httpx
import pytest

from app.services.llm import Intent, _fallback_classification, classify_intent


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        ("Show me SUVs under $35,000", Intent.INVENTORY_SEARCH),
        ("Tell me about #2", Intent.VEHICLE_DETAILS),
        ("Show me something similar to #1", Intent.SIMILAR_VEHICLES),
        ("What's the monthly payment on the first car?", Intent.PAYMENT_INQUIRY),
        (
            "What's the monthly payment on the first car? I have good credit and $5,000 down",
            Intent.PAYMENT_ESTIMATE
        ),
        ("Can I get pre-approved?", Intent.CREDIT_PREQUALIFICATION),
        ("Hello there", Intent.GREETING),
    ],
)
def test_fallback_classifies_all_demo_intents(message: str, expected_intent: Intent):
    """Fallback rules should route each primary demo utterance to the right intent."""
    result = _fallback_classification(message)
    assert result.intent == expected_intent


@pytest.mark.asyncio
async def test_classify_intent_uses_fallback_when_ollama_unavailable(monkeypatch):
    """`classify_intent` should return rule-based fallback if Ollama is unreachable."""

    async def raise_connect_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", raise_connect_error)

    result = await classify_intent("Show me SUVs under $30,000")

    assert result.intent == Intent.INVENTORY_SEARCH
    assert result.raw_response == "fallback"
