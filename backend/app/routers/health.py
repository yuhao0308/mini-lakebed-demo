"""
Health check router.
"""

from fastapi import APIRouter
from app.models.schemas import ComponentStatus
from app.services.database import execute_one
from app.services.authorization import get_authorization_service
import ollama

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check health of all system components."""
    
    # Check database
    try:
        await execute_one("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check LLM (Ollama)
    try:
        # Quick ping to Ollama
        models = ollama.list()
        llm_status = "ok" if models else "no models"
    except Exception as e:
        llm_status = f"error: {str(e)}"
    
    # Vector store check would go here
    vector_status = "ok"  # Placeholder for ChromaDB check

    try:
        auth_status = get_authorization_service().get_status()
    except Exception as e:
        auth_status = {"mode": "error", "reason": str(e)}
    
    overall = "healthy" if all(
        s == "ok" for s in [db_status, llm_status, vector_status]
    ) else "degraded"
    
    return {
        "status": overall,
        "version": "0.1.0",
        "components": ComponentStatus(
            database=db_status,
            llm=llm_status,
            vector_store=vector_status
        ).model_dump(),
        "agent_graph": "langgraph",
        "agent_nodes": [
            "conversationalist",
            "compliance_sentinel",
            "inventory_graph",
            "fin_calc_solver",
            "credit_officer",
            "responder",
        ],
        "authorization": auth_status,
    }
