"""
Health check router.
"""

from fastapi import APIRouter
from app.models.schemas import HealthResponse, ComponentStatus
from app.services.database import execute_one
import ollama

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
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
    
    overall = "healthy" if all(
        s == "ok" for s in [db_status, llm_status, vector_status]
    ) else "degraded"
    
    return HealthResponse(
        status=overall,
        version="0.1.0",
        components=ComponentStatus(
            database=db_status,
            llm=llm_status,
            vector_store=vector_status
        )
    )
