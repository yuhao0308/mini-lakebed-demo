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

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed_data  # Load synthetic data
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
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
