# Mini-Lakebed Demo Walkthrough (Exact Prompts)

Use this script for a clean, repeatable 15-minute walkthrough of Scenes 1-4.

## Pre-Demo Setup

1. Start the stack:

```bash
cd mini-lakebed-demo
./scripts/start_demo.sh
```

2. Open the UI at `http://localhost:5173`, then click **Chat**.
3. Keep one terminal visible for API logs if you want live observability.

## Scene 1: Inventory Transparency (0:00-4:00)

### Prompt 1
`Show me SUVs between $20,000 and $35,000`

Expected:
- assistant returns an inventory result set
- 100-result cap warning may appear depending on data distribution

### Prompt 2
`Tell me about the first one`

Expected:
- assistant sets session context to vehicle #1

### Prompt 3
`What's the monthly payment on this car?`

Expected:
- assistant asks for missing credit/down-payment info (no raw rate quote yet)

## Scene 2: Soft-Pull Handshake (4:00-8:00)

### Prompt 4
`Can I get pre-approved for this one?`

Expected:
- consent/prequalification guidance appears
- in UI flows with consent card enabled, user can accept soft-pull consent

### Prompt 5
`I have good credit and $5,000 down`

Expected:
- assistant proceeds to estimate flow using provided inputs

## Scene 3: Interactive Payment Structuring (8:00-12:00)

### Prompt 6
`What is the monthly payment on the first car? I have good credit and $5,000 down`

Expected:
- payment estimate is returned in one shot
- no repeated clarification loop

### Prompt 7
`What if I put $7,000 down instead?`

Expected:
- updated monthly payment is lower than prior estimate

### Prompt 8
`What if I do 48 months?`

Expected:
- payment recalculates for shorter term

## Scene 4: Adverse Action + PDF (12:00-15:00)

Use the sample PDF endpoint (predictable and deterministic for live demos):

Open in browser:
- `http://localhost:8000/api/documents/adverse-action/sample?language=en`
- `http://localhost:8000/api/documents/adverse-action/sample?language=es`

Expected:
- downloadable PDF response
- contains reason codes and adverse-action language

Optional API call for custom payload:

```bash
curl -X POST "http://localhost:8000/api/documents/adverse-action/pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "notice_id": "AA-DEMO-001",
    "applicant_name": "Demo Customer",
    "decision_date": "2026-02-12",
    "bureau_source": "Experian",
    "score_date": "2026-02-12",
    "reasons": [
      {"code": "A01", "text": "Too many inquiries in the last 12 months"},
      {"code": "B02", "text": "Amount owed on revolving accounts is too high"}
    ],
    "counter_offer": {
      "adjusted_term_months": 48,
      "adjusted_apr": 12.99,
      "adjusted_monthly_payment": 785.50,
      "required_down_payment": 3000.00
    },
    "language": "en"
  }' --output adverse_action_demo.pdf
```

## Backup Prompts (If You Need a Quick Reset)

- `Show me sedans around 25k`
- `Tell me about #2`
- `What's the monthly payment on #2 with 720 credit and $3,000 down?`
- `Can I get pre-approved?`
