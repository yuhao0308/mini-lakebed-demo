"""
Utilities for frontend visualization of the agent LangGraph.
"""

from __future__ import annotations

from app.services.agent_graph import AGENT_EDGES, AGENT_GRAPH, AGENT_NODES


def get_graph_mermaid() -> str:
    """Return Mermaid diagram of the agent graph."""
    try:
        graph_obj = AGENT_GRAPH.get_graph()
        if hasattr(graph_obj, "draw_mermaid"):
            return graph_obj.draw_mermaid()
    except Exception:
        pass

    lines = ["graph TD"]
    for edge in AGENT_EDGES:
        source = edge["from"]
        target = edge["to"]
        condition = edge.get("condition")
        if condition:
            lines.append(f"    {source} -->|{condition}| {target}")
        else:
            lines.append(f"    {source} --> {target}")
    return "\n".join(lines)


def get_graph_json() -> dict:
    """Return nodes/edges as JSON for frontend visualization."""
    return {
        "nodes": [{"id": name} for name in AGENT_NODES],
        "edges": AGENT_EDGES,
    }

