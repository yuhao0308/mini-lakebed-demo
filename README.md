# Mini-Lakebed Demo MVP

A governed agentic AI demo for automotive inventory Q&A and payment estimates.

> **DEMO ONLY:** All lender rules, interest rates, and payment estimates are **SYNTHETIC** and do not represent real financial products. This system is not intended for actual lending decisions.

## Features

- Natural language inventory search
- Payment estimates with deterministic calculation
- Full audit trail with rule citations
- Guardrails preventing LLM hallucination
- FCRA consent workflow
- PII scrubbing middleware
- Bilingual support (English / Spanish)
- PDF generation (adverse action notices, offering price sheets)

## Architecture

```
┌──────────────────────┐         ┌──────────────────────────────────┐
│  Railway (Cloud)     │         │  Mac Mini (Local)                │
│                      │         │                                  │
│  React + Vite        │  HTTPS  │  FastAPI (:8000)                 │
│  (static frontend)   │────────>│  Ollama  (llama3.1 / nomic)     │
│  served by `serve`   │  tunnel │  SQLite + ChromaDB               │
│  on :8080            │         │  MongoDB (:27017)                │
└──────────────────────┘         └──────────────────────────────────┘
        │                                     │
        │  Cloudflare Quick Tunnel            │
        │  *.trycloudflare.com ──────────────>│
```

| Component | Tech | Runs on |
|---|---|---|
| Frontend | React 19, Vite, Recharts, Lucide | Railway |
| Backend | Python FastAPI, LangGraph | Mac Mini |
| LLM | Ollama (llama3.1:8b) | Mac Mini |
| Embeddings | Ollama (nomic-embed-text) | Mac Mini |
| Database | SQLite + ChromaDB | Mac Mini |
| Tunnel | Cloudflare Quick Tunnel | Mac Mini |

## Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed (`brew install ollama`)
- `cloudflared` installed (`brew install cloudflare/cloudflare/cloudflared`)
- MongoDB running locally (for audit/compliance logs)

### Pull Ollama Models

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Local Development

### One-Command Startup

```bash
cd mini-lakebed-demo
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
./scripts/start_demo.sh
```

This will:
- Seed inventory/customers/deals/compliance logs (1200 / 100 / 50 / 1000)
- Start backend at http://localhost:8000
- Start frontend at http://localhost:5173

Use `./scripts/start_demo.sh --no-seed` to restart services without reseeding.

### Manual Startup

```bash
cd mini-lakebed-demo
source venv/bin/activate
python -m scripts.seed_data --vehicles 1200 --customers 100 --deals 50 --compliance-logs 1000

# Terminal 1 — backend
cd backend
../venv/bin/python -m uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

## Deployment

### Frontend — Railway

Deployed at: `https://mini-lakebed-demo-production.up.railway.app`

Railway builds the frontend using the `Dockerfile` at the project root (multi-stage: build with Vite, serve with `serve`). Configuration is in `railway.toml`.

#### Railway Environment Variables

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Cloudflare Tunnel URL to the Mac Mini backend (must be updated when tunnel restarts) |

### Backend — Mac Mini

The backend runs locally on the Mac Mini. To expose it to the Railway frontend, use a Cloudflare Quick Tunnel.

#### Start the backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Start the Cloudflare Tunnel (persistent)

```bash
nohup cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
```

Get the assigned URL:

```bash
grep "trycloudflare.com" /tmp/cloudflared.log
```

Output example: `https://some-random-words.trycloudflare.com`

#### When the tunnel restarts (you get a new URL)

1. Start the tunnel:
   ```bash
   nohup cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
   ```
2. Get the new URL:
   ```bash
   grep "trycloudflare.com" /tmp/cloudflared.log
   ```
3. Update `VITE_API_BASE_URL` in Railway with the new URL
4. Railway auto-redeploys with the new URL baked into the frontend build

#### Quick Tunnel Caveats

| Issue | Detail |
|---|---|
| URL changes every restart | Must update `VITE_API_BASE_URL` in Railway and wait for redeploy |
| No custom domain | Random `*.trycloudflare.com` subdomain |
| No built-in auth | Anyone with the URL can reach the backend (see Tunnel Secret below) |

### Tunnel Secret (optional)

Protect the backend from unauthorized access through the public tunnel URL.

1. Set `TUNNEL_SECRET` in `backend/.env`:
   ```
   TUNNEL_SECRET=your-strong-random-secret
   ```
2. Set the same `TUNNEL_SECRET` value in Railway environment variables
3. Update frontend API calls to include the header:
   ```js
   headers: { 'X-Tunnel-Secret': process.env.TUNNEL_SECRET }
   ```

The middleware skips enforcement when `TUNNEL_SECRET` is not set, so local development works without it.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Conversational AI interface |
| `/api/inventory` | GET | Search/filter vehicle inventory |
| `/api/payments` | POST | Calculate payment estimates |
| `/api/consent` | POST | Submit FCRA consent |
| `/api/consent/check/{id}` | GET | Check consent status |
| `/api/documents/adverse-action/pdf` | POST | Generate adverse action PDF |
| `/api/documents/offering-price/pdf` | POST | Generate offering price PDF |
| `/health` | GET | Health check |
| `/` | GET | API info |

## Project Structure

```
mini-lakebed-demo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # LLM, database, vector store
│   │   └── middleware/          # PII scrubber
│   ├── requirements.txt
│   └── .env                     # Local env vars (gitignored)
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── services/api.ts      # API client
│   │   ├── hooks/               # Custom hooks (language, etc.)
│   │   ├── i18n/                # en.json, es.json
│   │   └── styles/              # CSS design tokens
│   ├── vite.config.ts
│   └── package.json
├── data/                        # Reference data (lender programs)
├── docs/                        # Specs, demo scripts, decisions
├── Dockerfile                   # Multi-stage build for Railway
├── railway.toml                 # Railway deployment config
└── README.md
```

## License

Demo/Educational Use Only
