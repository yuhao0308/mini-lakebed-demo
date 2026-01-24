# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification Sources (Must Read)

Before implementing features, review these authoritative specs:
- `docs/specs/01_general_proposal.md` - Business context, market analysis, strategic vision
- `docs/specs/02_strategic_blueprint.md` - Neuro-symbolic architecture, personas, user stories, compliance requirements
- `docs/specs/03_implementation_dummy_data_plan.md` - Data schemas, pipeline architecture, dummy data specs, governance model

**Rule:** Any implementation decision must trace back to these specs. If a spec is missing or ambiguous, document the decision in `docs/DECISIONS.md` before coding.

## Project Overview

Mini-Lakebed Demo MVP: A governed agentic AI for automotive inventory Q&A and payment estimates. All lender rules and payment estimates are **synthetic** (demo only).

**Tech Stack:** Python FastAPI (backend) + React/TypeScript/Vite (frontend) + SQLite + ChromaDB + Ollama (llama3.1:8b)

## Development Commands

### Backend
```bash
cd mini-lakebed-demo/backend
source venv/bin/activate
pip install -r requirements.txt

# Seed database and build vector index
python -m scripts.seed_data
python -m scripts.index_vehicles

# Run server
uvicorn app.main:app --reload --port 8000

# Tests
pytest tests/
pytest tests/test_session_context.py -v  # specific test
```

### Frontend
```bash
cd mini-lakebed-demo/frontend
npm install
npm run dev      # dev server at http://localhost:5173
npm run build    # production build
npm run lint     # ESLint
```

### Ollama
```bash
ollama pull llama3.1:8b
ollama serve
```

## Architecture

### Core Flow
1. **Chat API** (`POST /api/chat`) receives user message with session_id
2. **Intent Classification** (Ollama or regex fallback) extracts intent and entities
3. **Route to Handler** based on intent:
   - `INVENTORY_SEARCH` → SQLite query
   - `VEHICLE_DETAILS` → Resolve references ("#3", "that one"), fetch details
   - `SIMILAR_VEHICLES` → ChromaDB semantic search
   - `PAYMENT_ESTIMATE` → Deterministic calculator (never LLM-generated)
   - `CLARIFICATION` → Ask user to disambiguate
4. **Response** includes session_id, markdown response, tool_calls[], metadata

### Critical Design Constraints

**Payment Guardrails:** The calculator (`backend/app/services/calculator.py`) is the ONLY source of truth for payment amounts. LLM classifies intent and formats responses but never generates payment values. Every quote cites a lender_rule by rule_id.

**Session Context:** In-memory state tracking (`backend/app/services/session_context.py`) enables:
- `current_vehicle` - Last viewed vehicle
- `recent_vehicles` - Last search results (enables "#3" references)
- `awaiting_input` - State machine: "clarification" | "confirm_payment_estimate" | "payment_info" | None
- `get_vehicle_by_reference()` - Resolves "#3" → recent_vehicles[2], "that one" → current_vehicle

**Fallback Resilience:** If Ollama fails, regex-based intent classification kicks in automatically.

### Key Files
- `backend/app/routers/chat.py` - Main chat handler with intent routing
- `backend/app/services/llm.py` - Intent classification + entity extraction
- `backend/app/services/calculator.py` - Deterministic payment calculation
- `backend/app/services/session_context.py` - Session state management
- `backend/app/services/vector_store.py` - ChromaDB semantic search
- `backend/app/models/schemas.py` - Pydantic models
- `frontend/src/components/Chat/ChatPane.tsx` - Chat UI

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/chat` | Conversational interface |
| GET | `/api/search_inventory` | Direct inventory search |
| GET | `/api/vehicle/{id}` | Vehicle details |
| POST | `/api/estimate_payment` | Calculate payment |
| GET | `/health` | Health check |

## Database Schema (SQLite)

- `inventory` - Vehicles (vin, make, model, year, price, mileage, status, etc.)
- `lender_rules` - Synthetic financing rules (rule_id, credit_tier, min/max_fico, apr, max_ltv)
- `audit_logs` - Request/response audit trail with rule citations
- `sessions` - Chat session metadata

## Adding New Features

### New Intent
1. Add to `Intent` enum in `backend/app/services/llm.py`
2. Add keywords to `_fallback_classification()`
3. Add handler `_handle_*()` in `backend/app/routers/chat.py`
4. Add routing case in `_route_intent()`

### New Lender Rule
Insert into `lender_rules` table with: rule_id, lender_name, credit_tier, min/max_fico, term range, base_apr, max_ltv

## Debugging

- **Empty vehicle list:** Run `python -m scripts.seed_data` and `python -m scripts.index_vehicles`
- **Ollama errors:** Ensure `ollama serve` is running and model is pulled
- **Payment "no matching rule":** Check FICO (650+), term (48/60/72), LTV (≤1.20) against lender_rules
