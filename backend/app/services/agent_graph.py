"""
LangGraph wrapper for chat agent orchestration.

This module keeps existing handler logic unchanged and orchestrates routing via
LangGraph nodes and edges.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from importlib import import_module
import inspect
from typing import Any, Optional, TypedDict, cast

try:
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:
    # Offline fallback: minimal state graph implementation with the same methods
    # used by this module (compile, ainvoke, get_graph/draw_mermaid).
    START = "START"
    END = "END"

    class _FallbackGraphView:
        def __init__(self, edges: list[tuple[str, str]]):
            self._edges = edges

        def draw_mermaid(self) -> str:
            lines = ["graph TD"]
            for source, target in self._edges:
                lines.append(f"    {source} --> {target}")
            return "\n".join(lines)

    class _FallbackCompiledGraph:
        def __init__(
            self,
            nodes: dict,
            edges: dict,
            conditional_edges: dict,
        ):
            self._nodes = nodes
            self._edges = edges
            self._conditional_edges = conditional_edges

        async def ainvoke(self, state: dict) -> dict:
            working_state = dict(state)
            next_nodes = self._edges.get(START, [END])
            current = next_nodes[0] if next_nodes else END

            while current != END:
                node_fn = self._nodes[current]
                result = node_fn(working_state)
                if inspect.isawaitable(result):
                    result = await result
                if result:
                    working_state.update(result)

                if current in self._conditional_edges:
                    router, route_map = self._conditional_edges[current]
                    route_key = router(working_state)
                    current = route_map.get(route_key, route_key)
                    continue

                next_nodes = self._edges.get(current, [END])
                current = next_nodes[0] if next_nodes else END

            return working_state

        def get_graph(self):
            edges = []
            for source, targets in self._edges.items():
                for target in targets:
                    edges.append((source, target))
            for source, (_, route_map) in self._conditional_edges.items():
                for target in route_map.values():
                    edges.append((source, target))
            return _FallbackGraphView(edges)

    class StateGraph:  # type: ignore[override]
        def __init__(self, _state_type):
            self._nodes = {}
            self._edges = {}
            self._conditional_edges = {}

        def add_node(self, name: str, fn):
            self._nodes[name] = fn

        def add_edge(self, source: str, target: str):
            self._edges.setdefault(source, []).append(target)

        def add_conditional_edges(self, source: str, router, route_map: Optional[dict] = None):
            self._conditional_edges[source] = (router, route_map or {})

        def compile(self):
            return _FallbackCompiledGraph(
                nodes=self._nodes,
                edges=self._edges,
                conditional_edges=self._conditional_edges,
            )

from app.services.compliance_sentinel import ComplianceSentinel
from app.services.database import execute_one
from app.services.llm import ExtractedEntities, Intent, LLMResult, classify_intent
from app.services.session_context import (
    add_chat_message,
    get_current_vehicle,
    resolve_vehicle_reference,
    update_awaiting_input,
    update_current_vehicle,
)


INVENTORY_INTENTS = {
    Intent.INVENTORY_SEARCH.value,
    Intent.VEHICLE_DETAILS.value,
    Intent.SIMILAR_VEHICLES.value,
}
PAYMENT_INTENTS = {
    Intent.PAYMENT_INQUIRY.value,
    Intent.PAYMENT_ESTIMATE.value,
}
SIMPLE_RESPONSE_INTENTS = {
    Intent.GREETING.value,
    Intent.OUT_OF_SCOPE.value,
    Intent.CLARIFICATION.value,
}

AGENT_NODES = [
    "conversationalist",
    "compliance_sentinel",
    "inventory_graph",
    "fin_calc_solver",
    "credit_officer",
    "responder",
    "session_updater",
]

AGENT_EDGES = [
    {"from": "START", "to": "conversationalist"},
    {"from": "conversationalist", "to": "compliance_sentinel"},
    {"from": "compliance_sentinel", "to": "inventory_graph", "condition": "inventory_intents"},
    {"from": "compliance_sentinel", "to": "fin_calc_solver", "condition": "payment_intents"},
    {"from": "compliance_sentinel", "to": "credit_officer", "condition": "credit_prequalification"},
    {"from": "compliance_sentinel", "to": "responder", "condition": "blocked_or_simple"},
    {"from": "inventory_graph", "to": "session_updater"},
    {"from": "fin_calc_solver", "to": "session_updater"},
    {"from": "credit_officer", "to": "session_updater"},
    {"from": "responder", "to": "session_updater"},
    {"from": "session_updater", "to": "END"},
]


class AgentState(TypedDict):
    # Input
    session_id: str
    user_message: str
    # Classification (set by conversationalist node)
    intent: Optional[str]
    entities: Optional[dict]
    confidence: float
    llm_result: Optional[Any]
    # Compliance gate output
    compliance_blocked: bool
    compliance_response: Optional[str]
    # Handler output
    response_text: str
    tool_calls: list
    metadata: dict


def build_initial_state(
    session_id: str,
    user_message: str,
    llm_result: Optional[LLMResult] = None,
) -> AgentState:
    """Create an initial LangGraph state payload."""
    return AgentState(
        session_id=session_id,
        user_message=user_message,
        intent=None,
        entities=None,
        confidence=0.0,
        llm_result=llm_result,
        compliance_blocked=False,
        compliance_response=None,
        response_text="",
        tool_calls=[],
        metadata={},
    )


def _to_intent_value(intent: Any) -> str:
    if intent is None:
        return ""
    if isinstance(intent, Intent):
        return intent.value
    if hasattr(intent, "value"):
        return str(intent.value)
    return str(intent).lower()


def _entities_to_dict(entities: Any) -> dict:
    if entities is None:
        return {}
    if isinstance(entities, dict):
        return entities
    if is_dataclass(entities):
        return asdict(entities)
    if hasattr(entities, "__dict__"):
        return dict(entities.__dict__)
    return {}


def _entities_from_state(state: AgentState) -> ExtractedEntities:
    raw = state.get("entities") or {}
    if isinstance(raw, ExtractedEntities):
        return raw
    if not isinstance(raw, dict):
        return ExtractedEntities()

    allowed = {field: raw.get(field) for field in ExtractedEntities.__dataclass_fields__.keys()}
    return ExtractedEntities(**allowed)


def _with_node_metadata(state: AgentState, node_name: str) -> dict:
    metadata = dict(state.get("metadata") or {})
    visited = list(metadata.get("visited_nodes", []))
    visited.append(node_name)
    metadata["visited_nodes"] = visited
    metadata["last_node"] = node_name
    return metadata


def _get_chat_module():
    return import_module("app.routers.chat")


async def _resolve_vehicle_id_for_compliance(session_id: str, entities: dict) -> Optional[int]:
    """
    Resolve a target vehicle for compliance checks.

    Uses session context first, then explicit references, then make/model lookup.
    """
    vehicle = await get_current_vehicle(session_id)
    if vehicle and vehicle.get("id") is not None:
        return int(vehicle["id"])

    explicit_vehicle_id = entities.get("vehicle_id")
    if explicit_vehicle_id is not None:
        return int(explicit_vehicle_id)

    vehicle_reference = entities.get("vehicle_reference")
    if vehicle_reference:
        vehicle = await resolve_vehicle_reference(session_id, vehicle_reference)
        if vehicle and vehicle.get("id") is not None:
            await update_current_vehicle(session_id, vehicle)
            return int(vehicle["id"])

    if entities.get("make") or entities.get("model"):
        conditions = ["status = 'available'"]
        params = []
        if entities.get("make"):
            conditions.append("LOWER(make) LIKE LOWER(?)")
            params.append(f"%{entities['make']}%")
        if entities.get("model"):
            conditions.append("LOWER(model) LIKE LOWER(?)")
            params.append(f"%{entities['model']}%")
        if entities.get("min_year"):
            conditions.append("year = ?")
            params.append(entities["min_year"])

        query = f"SELECT * FROM inventory WHERE {' AND '.join(conditions)} LIMIT 1"
        vehicle = await execute_one(query, tuple(params))
        if vehicle and vehicle.get("id") is not None:
            await update_current_vehicle(session_id, vehicle)
            return int(vehicle["id"])

    return None


async def _conversationalist_node(state: AgentState) -> AgentState:
    llm_result = cast(Optional[LLMResult], state.get("llm_result"))
    if llm_result is None:
        llm_result = await classify_intent(state["user_message"])

    intent_value = _to_intent_value(llm_result.intent)
    return cast(
        AgentState,
        {
            "intent": intent_value,
            "entities": _entities_to_dict(llm_result.entities),
            "confidence": float(llm_result.confidence or 0.0),
            "llm_result": llm_result,
            "metadata": _with_node_metadata(state, "conversationalist"),
        },
    )


async def _compliance_sentinel_node(state: AgentState) -> AgentState:
    """
    Compliance sentinel observes all intents but does NOT block payment intents.

    The payment handlers (_handle_payment_inquiry, _handle_payment_estimate) have
    their own SB 766 compliance logic that builds the offering price disclosure,
    records it, and sets the proper awaiting_input state.  Blocking here would
    short-circuit that richer handler logic and return a bare message instead.

    The sentinel still logs the compliance check for the audit trail.
    """
    intent = _to_intent_value(state.get("intent"))

    # Log compliance observation for audit trail (non-blocking)
    if intent in PAYMENT_INTENTS:
        entities = state.get("entities") or {}
        vehicle_id = await _resolve_vehicle_id_for_compliance(state["session_id"], entities)
        if vehicle_id is not None:
            sentinel = ComplianceSentinel()
            violation = await sentinel.enforce_offering_price_first(
                intent=intent,
                session_id=state["session_id"],
                vehicle_id=vehicle_id,
            )
            if violation:
                import logging
                logging.getLogger(__name__).info(
                    "Compliance sentinel observed SB766 violation for vehicle %s "
                    "in session %s - delegating to handler for proper disclosure flow",
                    vehicle_id, state["session_id"],
                )

    return cast(
        AgentState,
        {
            "compliance_blocked": False,
            "compliance_response": None,
            "metadata": _with_node_metadata(state, "compliance_sentinel"),
        },
    )


async def _inventory_graph_node(state: AgentState) -> AgentState:
    chat_module = _get_chat_module()
    entities = _entities_from_state(state)
    intent = _to_intent_value(state.get("intent"))
    tool_calls = []

    if intent == Intent.INVENTORY_SEARCH.value:
        response_text, tool_calls = await chat_module._handle_inventory_search(  # noqa: SLF001
            entities, tool_calls, state["session_id"]
        )
    elif intent == Intent.VEHICLE_DETAILS.value:
        response_text, tool_calls = await chat_module._handle_vehicle_details(  # noqa: SLF001
            entities, tool_calls, state["session_id"]
        )
    else:
        response_text, tool_calls = await chat_module._handle_similar_vehicles(  # noqa: SLF001
            entities, tool_calls, state["user_message"], state["session_id"]
        )

    return cast(
        AgentState,
        {
            "response_text": response_text,
            "tool_calls": tool_calls,
            "metadata": _with_node_metadata(state, "inventory_graph"),
        },
    )


async def _fin_calc_solver_node(state: AgentState) -> AgentState:
    chat_module = _get_chat_module()
    entities = _entities_from_state(state)
    intent = _to_intent_value(state.get("intent"))
    tool_calls = []

    if intent == Intent.PAYMENT_INQUIRY.value:
        response_text, tool_calls = await chat_module._handle_payment_inquiry(  # noqa: SLF001
            entities, tool_calls, state["session_id"]
        )
    else:
        response_text, tool_calls = await chat_module._handle_payment_estimate(  # noqa: SLF001
            entities, tool_calls, state["session_id"]
        )

    return cast(
        AgentState,
        {
            "response_text": response_text,
            "tool_calls": tool_calls,
            "metadata": _with_node_metadata(state, "fin_calc_solver"),
        },
    )


async def _credit_officer_node(state: AgentState) -> AgentState:
    chat_module = _get_chat_module()
    entities = _entities_from_state(state)
    response_text, tool_calls = await chat_module._handle_credit_prequalification(  # noqa: SLF001
        entities, [], state["session_id"]
    )

    return cast(
        AgentState,
        {
            "response_text": response_text,
            "tool_calls": tool_calls,
            "metadata": _with_node_metadata(state, "credit_officer"),
        },
    )


async def _responder_node(state: AgentState) -> AgentState:
    intent = _to_intent_value(state.get("intent"))

    if state.get("compliance_blocked"):
        response = state.get("compliance_response") or (
            "Before we get to payments, we must first disclose the Offering Price."
        )
    elif intent == Intent.GREETING.value:
        response = (
            "Hello! I'm your Mini-Lakebed assistant. I can help you:\n\n"
            "🚗 **Search our inventory** - \"Show me SUVs under $35,000\"\n"
            "🔍 **Find similar vehicles** - \"Show me cars like the Toyota Camry\"\n"
            "💰 **Estimate payments** - \"What's the payment on a $25,000 car?\"\n\n"
            "What would you like to know?"
        )
    elif intent == Intent.OUT_OF_SCOPE.value:
        response = (
            "I appreciate your question, but that's outside what I can help with. "
            "I'm specialized in:\n\n"
            "- Searching our vehicle inventory\n"
            "- Finding similar vehicles\n"
            "- Providing payment estimates\n\n"
            "Would you like help with any of those?"
        )
    else:
        await update_awaiting_input(state["session_id"], "clarification")
        response = (
            "I want to make sure I understand correctly. Are you asking about:\n\n"
            "**A)** Finding vehicles in our inventory\n"
            "**B)** Finding similar vehicles\n"
            "**C)** Estimating monthly payments\n\n"
            "Please let me know which one!"
        )

    return cast(
        AgentState,
        {
            "response_text": response,
            "tool_calls": [],
            "metadata": _with_node_metadata(state, "responder"),
        },
    )


async def _session_updater_node(state: AgentState) -> AgentState:
    if state.get("response_text"):
        await add_chat_message(state["session_id"], "assistant", state["response_text"])

    return cast(
        AgentState,
        {
            "metadata": _with_node_metadata(state, "session_updater"),
        },
    )


def _route_after_compliance(state: AgentState) -> str:
    if state.get("compliance_blocked"):
        return "responder"

    intent = _to_intent_value(state.get("intent"))
    if intent in INVENTORY_INTENTS:
        return "inventory_graph"
    if intent in PAYMENT_INTENTS:
        return "fin_calc_solver"
    if intent == Intent.CREDIT_PREQUALIFICATION.value:
        return "credit_officer"
    if intent in SIMPLE_RESPONSE_INTENTS:
        return "responder"
    return "responder"


def _build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("conversationalist", _conversationalist_node)
    graph.add_node("compliance_sentinel", _compliance_sentinel_node)
    graph.add_node("inventory_graph", _inventory_graph_node)
    graph.add_node("fin_calc_solver", _fin_calc_solver_node)
    graph.add_node("credit_officer", _credit_officer_node)
    graph.add_node("responder", _responder_node)
    graph.add_node("session_updater", _session_updater_node)

    graph.add_edge(START, "conversationalist")
    graph.add_edge("conversationalist", "compliance_sentinel")
    graph.add_conditional_edges(
        "compliance_sentinel",
        _route_after_compliance,
        {
            "inventory_graph": "inventory_graph",
            "fin_calc_solver": "fin_calc_solver",
            "credit_officer": "credit_officer",
            "responder": "responder",
        },
    )
    graph.add_edge("inventory_graph", "session_updater")
    graph.add_edge("fin_calc_solver", "session_updater")
    graph.add_edge("credit_officer", "session_updater")
    graph.add_edge("responder", "session_updater")
    graph.add_edge("session_updater", END)

    return graph.compile()


AGENT_GRAPH = _build_agent_graph()


async def invoke_agent_graph(
    session_id: str,
    user_message: str,
    llm_result: Optional[LLMResult] = None,
) -> AgentState:
    """
    Invoke the compiled LangGraph orchestration for one chat turn.
    """
    initial_state = build_initial_state(
        session_id=session_id,
        user_message=user_message,
        llm_result=llm_result,
    )
    result = await AGENT_GRAPH.ainvoke(initial_state)
    return cast(AgentState, result)
