# Mini-Lakebed Demo Script: "The Trust Protocol" (15 Minutes)

## Prerequisites

```bash
# One-command launch (seeds data + starts backend + frontend)
./scripts/start_demo.sh

# Or skip re-seeding if data is already loaded
./scripts/start_demo.sh --no-seed
```

**Services:**
- Frontend: http://localhost:5173
- Backend:  http://localhost:8000
- Health:   http://localhost:8000/health

**Fallback Mode:** Set `DEMO_FORCE_FALLBACK=1` for deterministic intent classification
(no Ollama required). The startup script handles this automatically.

---

## Scene 1: Inventory Transparency & SB 766 Offering Price (0:00 - 4:00)

### Talking Points
- Natural language inventory search
- SB 766 compliance: Offering Price must be disclosed before any payment discussion
- LangGraph agent orchestration visible in health endpoint

### Exact Prompts

**Step 1 — Search inventory:**
```
Show me Toyota Camry sedans under $30,000
```
> **Expected:** List of ~13 matching vehicles with prices and mileage

**Step 2 — Select a vehicle:**
```
Tell me about the first one
```
> **Expected:** Full vehicle details (price, mileage, color, fuel type, drivetrain)

**Step 3 — Ask about payment (triggers SB 766):**
```
How much is the monthly payment?
```
> **Expected:** System shows Offering Price disclosure BEFORE payment:
> - "Before we get to payments, the **Offering Price** for this **Toyota Camry** is **$XX,XXX**"
> - Includes: Base vehicle price + Doc fee breakdown
> - "Government taxes and registration fees are extra"
> - Then asks: "Would you like to see financing options?"

### What to Point Out
- The system did NOT just show a payment — it enforced SB 766 first
- The Compliance Sentinel agent intercepted the request
- Agent nodes visited: `conversationalist → compliance_sentinel → fin_calc_solver`

---

## Scene 2: Soft-Pull Consent Handshake (4:00 - 8:00)

### Talking Points
- FCRA compliance: Written consent required before credit check
- Consent logged with timestamp and IP
- SoftPullCard UI component renders in chat

### Exact Prompts

**Step 4 — Request pre-approval:**
```
Can I get approved?
```
> **Expected:** System asks for FCRA authorization:
> - "Before I can do a soft credit check, I need your authorization"
> - "A soft pull will **not** affect your credit score"
> - (Frontend shows SoftPullCard consent UI)

**Step 5 — (In the UI) Click "I Agree" on the SoftPullCard**

> **Expected:** Consent recorded. System asks for credit details.

### What to Point Out
- FCRA consent is a legal requirement — the system enforces it
- Consent logged with `consent_id`, `timestamp`, `expires_at` (30 days)
- The Credit Officer agent can only proceed after consent

---

## Scene 3: Penny-Perfect Deal Structuring (8:00 - 12:00)

### Talking Points
- Deterministic calculation — LLM NEVER generates payment amounts
- Day-count conventions (30/360, Actual/365, 365/360)
- Penny-perfect: $35k/5%/60mo = exactly $660.49

### Exact Prompts

**Step 6 — Provide credit info:**
```
I have good credit, score around 720, and $3000 down
```
> **Expected:** Payment estimate with full breakdown:
> - Monthly Payment: $XXX.XX/mo
> - APR: X.XX%
> - Term: 60 months
> - Down Payment: $3,000
> - Total Interest: $X,XXX.XX
> - Rule ID and Lender name cited

### What to Point Out
- Payment is deterministic — calculated by Fin_Calc_Solver, not the LLM
- Every quote cites a `rule_id` for audit trail
- The system uses `Decimal` arithmetic — no floating-point drift
- Interactive PaymentBreakdown component allows changing down payment/term

---

## Scene 4: Adverse Action with Reg B Reasons (12:00 - 15:00)

### Talking Points
- Regulation B requires SPECIFIC reasons for denial — never "bad credit"
- Counter-offer generation
- PDF download for formal notice
- Multi-language support (English/Spanish)

### Setup (New Session)

**Step 7 — Search and select a vehicle:**
```
Show me Honda vehicles
```
Then:
```
Tell me about the first one
```

**Step 8 — Request pre-approval with low score:**
```
Can I get approved?
```
> (SoftPullCard appears → click "I Agree")

Then provide low-score info in the chat or directly test the PDF endpoints.

### Demonstrating Adverse Action PDF

**Open in browser:**
- English: http://localhost:8000/api/documents/adverse-action/sample
- Spanish: http://localhost:8000/api/documents/adverse-action/sample?language=es

> **Expected PDF includes:**
> - Specific Reg B reason codes (NOT "bad credit"):
>   - "Too many inquiries in the last 12 months"
>   - "Amount owed on revolving accounts is too high"
> - Bureau source and score date
> - Counter-offer with alternative terms
> - Legal footer (ECOA + FCRA rights)

### Demonstrating Offering Price PDF

- http://localhost:8000/api/documents/offering-price/sample
- http://localhost:8000/api/documents/offering-price/sample?language=es

### What to Point Out
- System never says "bad credit" — only specific Reg B reason codes
- PDF is generated server-side for formal compliance record
- Spanish translation available for multi-lingual markets
- Counter-offer shows a path forward (higher down payment, shorter term)

---

## Bonus: Architecture & Governance

### Health Endpoint (show in browser)
```
http://localhost:8000/health
```
Shows:
- LangGraph agent orchestration with 6 named agents
- Authorization mode (OpenFGA or RBAC fallback)
- Database, LLM, and vector store status

### Key Architecture Points
- **5 AI Agents** orchestrated via LangGraph StateGraph
- **PII Scrubber** middleware strips SSN/DOB before LLM context
- **Audit Trail** with SHA-256 payload hashes for tamper evidence
- **Cross-Store Isolation** via OpenFGA-compatible ReBAC model
- **Ollama Fallback** — works without LLM for deterministic demos

### Data Volumes
- 1,200 vehicles in inventory
- 100 demo customers
- 50 demo deals in various states
- 1,000 pre-filled compliance logs
- 50 lender programs across 5 credit tiers
- 100 tax jurisdictions (CA, AZ, NV, TX, FL)
- 25 Reg B adverse action codes

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Empty vehicle list | `python -m scripts.seed_data --vehicles 1200` |
| Ollama errors | Set `DEMO_FORCE_FALLBACK=1` or run `ollama serve` |
| "No matching rule" on payment | Check FICO (650+), term (48/60/72), LTV (≤1.20) |
| Frontend can't connect | Verify backend running on port 8000, check CORS |
| PDF endpoints 404 | Use `/api/documents/adverse-action/sample` (not `/pdf`) |
