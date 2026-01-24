"""
Mini-Lakebed Demo MVP - FastAPI Application
A governed agentic AI demo for automotive inventory Q&A and payment estimates.

⚠️ DEMO ONLY: All lender rules and rates are SYNTHETIC.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import inventory, payments, chat, health, consent
from app.services.database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_database()
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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(payments.router, prefix="/api", tags=["Payments"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(consent.router, prefix="/api", tags=["Consent"])  # T03: FCRA consent


@app.get("/")
async def root():
    return {
        "message": "Mini-Lakebed Demo API",
        "version": "0.1.0",
        "disclaimer": "DEMO ONLY: All data and rates are synthetic.",
    }
