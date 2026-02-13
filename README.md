# Mini-Lakebed Demo MVP

A governed agentic AI demo for automotive inventory Q&A and payment estimates.

## ⚠️ DEMO DISCLAIMER

> **This is a demonstration system only.** All lender rules, interest rates, and payment estimates are **SYNTHETIC** and do not represent real financial products. This system is not intended for actual lending decisions.

## Features

- Natural language inventory search
- Payment estimates with deterministic calculation
- Full audit trail with rule citations
- Guardrails preventing LLM hallucination

## Tech Stack

- **Backend**: Python FastAPI
- **Database**: SQLite + ChromaDB
- **LLM**: Ollama (llama3.1)
- **Frontend**: React + Vite

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed (`brew install ollama`)

### One-Command Demo Startup

```bash
cd mini-lakebed-demo
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
./scripts/start_demo.sh
```

This single command will:
- seed inventory/customers/deals/compliance logs for demo (`1200 / 100 / 50 / 1000`)
- start backend (`http://localhost:8000`)
- start frontend (`http://localhost:5173`)

Use `./scripts/start_demo.sh --no-seed` to restart services without reseeding.

### Manual Startup

```bash
cd mini-lakebed-demo
source venv/bin/activate
python -m scripts.seed_data --vehicles 1200 --customers 100 --deals 50 --compliance-logs 1000

# terminal 1
cd backend
../venv/bin/python -m uvicorn app.main:app --reload

# terminal 2
cd frontend
npm run dev
```

### Pull Ollama Models

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Conversational interface |
| `/search_inventory` | GET | Filter inventory |
| `/vehicle/{id}` | GET | Get vehicle details |
| `/estimate_payment` | POST | Calculate payment |
| `/health` | GET | Health check |

## License

Demo/Educational Use Only
