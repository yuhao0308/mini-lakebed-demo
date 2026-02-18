"""
Mini-Lakebed Demo MVP - FastAPI Application
A governed agentic AI demo for automotive inventory Q&A and payment estimates.

⚠️ DEMO ONLY: All lender rules and rates are SYNTHETIC.

T05: Added PII scrubber middleware for governance.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.routers import inventory, payments, chat, health, consent, documents
from app.services.database import init_database
from app.middleware.pii_scrubber import get_pii_scrubber

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_database()
    try:
        from app.services.vector_store import get_collection
        await asyncio.to_thread(get_collection)
    except Exception:
        logger.warning("Vector store pre-warm failed during startup", exc_info=True)
    yield


app = FastAPI(
    title="Mini-Lakebed Demo",
    description="Governed agentic AI for automotive inventory Q&A and payment estimates. DEMO ONLY.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://mini-lakebed-demo-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Tunnel shared-secret middleware - protect public tunnel endpoint
TUNNEL_SECRET = os.environ.get("TUNNEL_SECRET")


@app.middleware("http")
async def tunnel_secret_middleware(request: Request, call_next):
    """Block requests missing the shared tunnel secret (when configured)."""
    if request.method == "OPTIONS":
        return await call_next(request)
    if TUNNEL_SECRET and request.headers.get("X-Tunnel-Secret") != TUNNEL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await call_next(request)


# T05: PII Scrubber middleware - attaches scrubber to request state
@app.middleware("http")
async def pii_scrubbing_middleware(request: Request, call_next):
    """
    Attach PII scrubber to request state for use in LLM calls.

    Per T05 spec: All data passed to LLM must go through PII scrubber.
    """
    request.state.pii_scrubber = get_pii_scrubber()
    response = await call_next(request)
    return response


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(payments.router, prefix="/api", tags=["Payments"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(consent.router, prefix="/api", tags=["Consent"])  # T03: FCRA consent
app.include_router(documents.router, prefix="/api", tags=["Documents"])  # T06: PDF generation


@app.get("/")
async def root():
    return {
        "message": "Mini-Lakebed Demo API",
        "version": "0.1.0",
        "disclaimer": "DEMO ONLY: All data and rates are synthetic.",
    }
