"""
Mini-Lakebed Demo MVP - FastAPI Application
A governed agentic AI demo for automotive inventory Q&A and payment estimates.

DEMO ONLY: All lender rules and rates are SYNTHETIC.

T05: Added PII scrubber middleware for governance.
"""

from dotenv import load_dotenv

load_dotenv(override=True)

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging

from app.routers import inventory, payments, chat, health, consent, documents
from app.services.database import init_database
from app.middleware.pii_scrubber import get_pii_scrubber

logger = logging.getLogger(__name__)
TUNNEL_SECRET = os.environ.get("TUNNEL_SECRET", "")

# Tunnel secret disabled — CORS origin allowlist is the access control for demo.
# Hard-coded to empty so a stale shell export can never re-enable blocking.
TUNNEL_SECRET = ""


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


ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://mini-lakebed-demo-production.up.railway.app",
]

app = FastAPI(
    title="Mini-Lakebed Demo",
    description="Governed agentic AI for automotive inventory Q&A and payment estimates. DEMO ONLY.",
    version="0.1.0",
    lifespan=lifespan,
)


# Registered before CORSMiddleware so that CORS becomes the outermost layer.
# Any early-exit response (e.g. 403) will still receive CORS headers because
# CORSMiddleware wraps the entire stack.
@app.middleware("http")
async def tunnel_secret_middleware(request: Request, call_next):
    """Block requests missing the shared tunnel secret (when configured)."""
    if request.method != "OPTIONS" and TUNNEL_SECRET:
        if request.headers.get("X-Tunnel-Secret") != TUNNEL_SECRET:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
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


# CORSMiddleware registered last → becomes outermost layer → CORS headers are
# added to every response, including early-exit 403s from tunnel_secret_middleware.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Allow any Cloudflare free-tunnel URL so VITE_API_BASE_URL changes
    # on each tunnel restart don't require a Railway rebuild.
    allow_origin_regex=r"https://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(payments.router, prefix="/api", tags=["Payments"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(consent.router, prefix="/api", tags=["Consent"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])


@app.get("/")
async def root():
    return {
        "message": "Mini-Lakebed Demo API",
        "version": "0.1.0",
        "disclaimer": "DEMO ONLY: All data and rates are synthetic.",
    }
