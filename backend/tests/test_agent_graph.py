"""
Tests for LangGraph-based chat orchestration wrapper.
"""

import pytest
from typing import Optional

from app.models.compliance import ComplianceViolation
from app.routers import chat
from app.services.agent_graph import (
    AGENT_GRAPH,
    AgentState,
    build_initial_state,
    invoke_agent_graph,
)
from app.services.compliance_sentinel import ComplianceSentinel
from app.services.graph_visualization import get_graph_mermaid
from app.services.llm import ExtractedEntities, Intent, LLMResult
from app.services.session_context import clear_session, update_current_vehicle


def _make_llm_result(intent: Intent, entities: Optional[ExtractedEntities] = None) -> LLMResult:
    return LLMResult(
        intent=intent,
        entities=entities or ExtractedEntities(),
        raw_response="test",
        confidence=0.95,
    )


def test_graph_compiles():
    """Graph compiles and exposes async invocation."""
    assert AGENT_GRAPH is not None
    assert hasattr(AGENT_GRAPH, "ainvoke")


@pytest.mark.asyncio
async def test_greeting_routes_to_responder():
    """GREETING intent routes to responder node."""
    session_id = "graph_greeting_test"
    await clear_session(session_id)

    result = await invoke_agent_graph(
        session_id=session_id,
        user_message="hello",
        llm_result=_make_llm_result(Intent.GREETING),
    )

    assert "responder" in result["metadata"]["visited_nodes"]
    assert result["response_text"].startswith("Hello!")


@pytest.mark.asyncio
async def test_inventory_search_routes_correctly(monkeypatch):
    """INVENTORY_SEARCH routes to inventory_graph node."""
    session_id = "graph_inventory_test"
    await clear_session(session_id)
    called = {"inventory": False}

    async def _fake_inventory_handler(entities, tool_calls, current_session_id):
        called["inventory"] = True
        assert current_session_id == session_id
        return "inventory-handler-response", [{"tool": "search_inventory"}]

    monkeypatch.setattr(chat, "_handle_inventory_search", _fake_inventory_handler)

    result = await invoke_agent_graph(
        session_id=session_id,
        user_message="show me SUVs",
        llm_result=_make_llm_result(Intent.INVENTORY_SEARCH),
    )

    assert called["inventory"] is True
    assert "inventory_graph" in result["metadata"]["visited_nodes"]
    assert result["response_text"] == "inventory-handler-response"


@pytest.mark.asyncio
async def test_payment_blocked_by_compliance(monkeypatch):
    """PAYMENT_ESTIMATE without disclosure routes to fin_calc_solver which handles SB 766 itself."""
    session_id = "graph_payment_blocked"
    await clear_session(session_id)
    await update_current_vehicle(session_id, {"id": 999, "make": "Toyota"})

    # The compliance sentinel no longer blocks at the graph level.
    # Instead the handler (_handle_payment_inquiry / _handle_payment_estimate)
    # contains the full SB 766 disclosure logic.
    called = {"handler": False}

    async def _fake_payment_estimate(entities, tool_calls, current_session_id):
        called["handler"] = True
        return "Offering Price disclosure shown by handler", []

    monkeypatch.setattr(chat, "_handle_payment_estimate", _fake_payment_estimate)

    result = await invoke_agent_graph(
        session_id=session_id,
        user_message="what is the payment?",
        llm_result=_make_llm_result(Intent.PAYMENT_ESTIMATE),
    )

    # Compliance sentinel observes but does not block
    assert result["compliance_blocked"] is False
    # Handler is called (it manages its own compliance logic)
    assert called["handler"] is True
    assert "fin_calc_solver" in result["metadata"]["visited_nodes"]


@pytest.mark.asyncio
async def test_payment_allowed_after_disclosure(monkeypatch):
    """PAYMENT_ESTIMATE after compliance pass routes to fin_calc_solver."""
    session_id = "graph_payment_allowed"
    await clear_session(session_id)
    await update_current_vehicle(session_id, {"id": 1001, "make": "Honda"})
    called = {"payment": False}

    async def _allowed(self, intent, session_id, vehicle_id):
        return None

    async def _fake_payment_estimate(entities, tool_calls, current_session_id):
        called["payment"] = True
        assert current_session_id == session_id
        return "payment-handler-response", [{"tool": "estimate_payment"}]

    monkeypatch.setattr(ComplianceSentinel, "enforce_offering_price_first", _allowed)
    monkeypatch.setattr(chat, "_handle_payment_estimate", _fake_payment_estimate)

    result = await invoke_agent_graph(
        session_id=session_id,
        user_message="payment estimate please",
        llm_result=_make_llm_result(
            Intent.PAYMENT_ESTIMATE,
            ExtractedEntities(credit_tier="prime", down_payment=5000),
        ),
    )

    assert result["compliance_blocked"] is False
    assert called["payment"] is True
    assert "fin_calc_solver" in result["metadata"]["visited_nodes"]
    assert result["response_text"] == "payment-handler-response"


@pytest.mark.asyncio
async def test_credit_routes_to_officer(monkeypatch):
    """CREDIT_PREQUALIFICATION routes to credit_officer node."""
    session_id = "graph_credit_test"
    await clear_session(session_id)
    called = {"credit": False}

    async def _fake_credit_handler(entities, tool_calls, current_session_id):
        called["credit"] = True
        assert current_session_id == session_id
        return "credit-handler-response", [{"tool": "credit_evaluation"}]

    monkeypatch.setattr(chat, "_handle_credit_prequalification", _fake_credit_handler)

    result = await invoke_agent_graph(
        session_id=session_id,
        user_message="can I get preapproved?",
        llm_result=_make_llm_result(Intent.CREDIT_PREQUALIFICATION),
    )

    assert called["credit"] is True
    assert "credit_officer" in result["metadata"]["visited_nodes"]
    assert result["response_text"] == "credit-handler-response"


def test_graph_state_includes_all_fields():
    """State TypedDict and initialized state include required keys."""
    expected = {
        "session_id",
        "user_message",
        "intent",
        "entities",
        "confidence",
        "llm_result",
        "compliance_blocked",
        "compliance_response",
        "response_text",
        "tool_calls",
        "metadata",
    }
    assert set(AgentState.__annotations__.keys()) == expected

    state = build_initial_state("state_test", "hello")
    assert expected.issubset(set(state.keys()))


def test_graph_visualization_mermaid():
    """Mermaid export returns a diagram with expected node names."""
    mermaid = get_graph_mermaid()
    assert isinstance(mermaid, str)
    assert "graph" in mermaid.lower()
    assert "conversationalist" in mermaid
    assert "compliance_sentinel" in mermaid
