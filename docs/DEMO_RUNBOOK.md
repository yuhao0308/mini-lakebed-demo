# Mini-Lakebed Demo Runbook

## For Live Stakeholder Demonstrations (15-20 Minutes)

> **DEMO ONLY:** All lender rules, interest rates, credit decisions, and payment estimates in this system are **synthetic**. Nothing in this demo represents a real financial product, real consumer data, or a real lending decision.

---

## Table of Contents

1. [Pre-Demo Setup](#1-pre-demo-setup)
2. [Scene 1: Inventory Search and Vehicle Selection (0:00-4:00)](#2-scene-1-inventory-search-and-vehicle-selection-000-400)
3. [Scene 2: SB 766 Offering Price Disclosure (4:00-7:00)](#3-scene-2-sb-766-offering-price-disclosure-400-700)
4. [Scene 3: FCRA Consent and Credit Pre-Qualification (7:00-11:00)](#4-scene-3-fcra-consent-and-credit-pre-qualification-700-1100)
5. [Scene 4: Deterministic Payment Estimates (11:00-14:00)](#5-scene-4-deterministic-payment-estimates-1100-1400)
6. [Scene 5: Adverse Action and PDF Documents (14:00-17:00)](#6-scene-5-adverse-action-and-pdf-documents-1400-1700)
7. [Scene 6: Architecture and Governance (17:00-20:00)](#7-scene-6-architecture-and-governance-1700-2000)
8. [Full Chatbot Conversation Script](#8-full-chatbot-conversation-script)
9. [Compliance Matrix](#9-compliance-matrix)
10. [Stakeholder Summary](#10-stakeholder-summary)
11. [Demo Limitations: What Is Mocked vs. Live](#11-demo-limitations-what-is-mocked-vs-live)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Pre-Demo Setup

### What You Need Running

| Service | How to Start | URL |
|---------|-------------|-----|
| Backend (FastAPI) | `./scripts/start_demo.sh` | http://localhost:8000 |
| Frontend (React) | Started by same script | http://localhost:5173 |
| Ollama (LLM) | `ollama serve` | localhost:11434 |

### Quick Start (One Command)

```bash
cd mini-lakebed-demo
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
./scripts/start_demo.sh
```

This seeds 1,200 vehicles, 100 customers, 50 deals, and 1,000 compliance logs, then starts both services.

### Fallback Mode (No Ollama Required)

Set `DEMO_FORCE_FALLBACK=1` before starting. The system uses regex-based intent classification instead of the LLM, producing deterministic results ideal for live demos.

### Pre-Demo Checklist

- [ ] Backend running at http://localhost:8000 (verify: open http://localhost:8000/health)
- [ ] Frontend running at http://localhost:5173
- [ ] Open browser to http://localhost:5173, click **Chat** in sidebar
- [ ] Keep a second browser tab open for PDF endpoints (Scene 5)
- [ ] Optional: Keep a terminal visible for API logs

---

## 2. Scene 1: Inventory Search and Vehicle Selection (0:00-4:00)

**What this scene demonstrates:** Natural language inventory search with price parsing, filtering, and vehicle reference resolution.

**Talking point for stakeholders:** "The system understands natural language. A salesperson or customer can ask questions the way they'd talk to a person, and the AI correctly interprets price ranges, vehicle types, and references like 'the first one' or '#3.'"

---

### Step 1 — Basic Inventory Search

**You type:**
```
Show me Toyota Camry sedans under $30,000
```

**Expected assistant output:**
```
Found [N] vehicles matching your criteria:

---

1. 2024 Toyota Camry LE
   $XX,XXX  •  XX,XXX mi  •  Sedan

2. 2023 Toyota Camry SE
   $XX,XXX  •  XX,XXX mi  •  Sedan

[... more results ...]

---

Say a number (e.g., "Tell me about #3") for details, or ask about payments!
```

**What the UI shows:** A scrollable horizontal row of vehicle cards beneath the chat message, each showing year, make, model, price, and mileage.

**Why this matters:** The system correctly parsed three filters from one sentence — make (Toyota), model (Camry), body style (sedan), and maximum price ($30,000). No dropdown menus or forms required.

---

### Step 2 — Price Parsing: "k" Notation and Reversed Ranges

**You type:**
```
Show me SUVs between $35k and $20,000
```

**Expected assistant output:** A list of SUVs priced between $20,000 and $35,000 (the system normalizes "$35k" to $35,000 and automatically corrects the reversed range).

**Why this matters:** Real users often type prices casually ("25k") or reverse the order. The AI handles both without errors. This is verified by automated E2E tests (inventory-search A3, A7, A8).

---

### Step 3 — Vehicle Reference Resolution

**You type:**
```
Tell me about #3
```

**Expected assistant output:**
```
2024 Toyota Camry [Trim]

Price: $XX,XXX
Mileage: XX,XXX miles
Color: [Color] / [Interior]
Fuel: Gasoline | Transmission: Automatic
Drivetrain: FWD | Engine: 2.5L 4-Cylinder

Would you like me to estimate the monthly payment for this vehicle?
```

**What the UI shows:** Full vehicle detail card with all specifications.

**Why this matters:** The system remembers the search results from Step 1 and resolves "#3" to the third vehicle. It also supports "the first one," "the last one," "the second car," and "that one" (referring to the most recently viewed vehicle). This is session context — no database ID required from the user.

---

### Step 4 — Similar Vehicles (Vector Search)

**You type:**
```
Show me similar vehicles
```

**Expected assistant output:**
```
Based on the 2024 Toyota Camry, here are similar vehicles:

• 2023 Honda Accord LX - $XX,XXX | Similarity: 92%
• 2024 Nissan Altima SV - $XX,XXX | Similarity: 88%
[... up to 5 results ...]

Would you like details on any of these?
```

**Why this matters:** This uses ChromaDB vector search (semantic similarity based on vehicle features), not simple keyword matching. The system found vehicles with similar characteristics, not just the same make/model.

---

## 3. Scene 2: SB 766 Offering Price Disclosure (4:00-7:00)

**What this scene demonstrates:** California SB 766 compliance — the system must disclose the total "Offering Price" (the all-in cash price) before discussing any monthly payment or financing terms.

**Talking point for stakeholders:** "Under California SB 766, a dealer must tell the customer the total cash price of the vehicle before talking about monthly payments. Our system enforces this automatically. The AI cannot skip this step, even if asked."

---

### Step 5 — Ask About Payments (Triggers SB 766 Disclosure)

**You type:**
```
How much is the monthly payment?
```

**Expected assistant output:**
```
Before we get to payments, the Offering Price for this
2024 Toyota Camry is $XX,XXX.

This includes:
- Base vehicle price: $XX,XXX
- Documentation fee: $85

Government taxes and registration fees are extra.

Would you like to see financing options for this vehicle?
```

**What the UI shows:** The offering price disclosure message with an itemized breakdown. A compliance_check tool call is logged with `sb766_offering_price` data.

**Why this matters:**
- The system did NOT show a payment. It intercepted the request and enforced the SB 766 disclosure first.
- The Compliance Sentinel agent (one of 6 AI agents in the system) blocked the payment quote until the offering price was disclosed.
- The disclosure is logged to the audit trail with a SHA-256 hash for tamper evidence.
- If the user asks about a different vehicle, the disclosure must happen again for that vehicle — it is per-vehicle, not per-session.

**Key compliance detail:** The offering price includes the base vehicle price, documentation fee, and any mandatory add-ons. It explicitly excludes government taxes and registration fees, which is exactly what SB 766 requires.

---

## 4. Scene 3: FCRA Consent and Credit Pre-Qualification (7:00-11:00)

**What this scene demonstrates:** The Fair Credit Reporting Act (FCRA) requires written consumer authorization before any credit inquiry. This system enforces that consent step with a dedicated UI component and audit logging.

**Talking point for stakeholders:** "Before we pull anyone's credit — even a soft pull that doesn't affect their score — federal law requires written consent. Our system won't proceed without it, and it logs the consent with a timestamp, IP address, and the exact legal text version the customer agreed to."

---

### Step 6 — Request Pre-Qualification

**You type:**
```
Can I get approved?
```

**Expected assistant output:**
```
I'd be happy to check financing options for the 2024 Toyota Camry!

Before I can do a soft credit check, I need your authorization.
This is required by the Fair Credit Reporting Act (FCRA).

Important: A soft pull will not affect your credit score.

Please review and accept the consent form to continue.
```

**What the UI shows:** A **SoftPullCard** consent component appears in the chat. It contains:
- A lock icon and "Credit Pre-Qualification" header
- FCRA-specific consent language: "I am providing 'written instructions' under the Fair Credit Reporting Act (FCRA) authorizing [Dealer Name] to obtain personal credit information..."
- A checkbox: "I have read and understand the above authorization"
- An "I Agree" button (disabled until checkbox is checked)
- A "Cancel" button
- A footer noting that IP address and timestamp will be recorded

**Why this matters:** The Credit Officer agent (the "Underwriter") cannot evaluate any credit application until FCRA consent is recorded. This is enforced in code, not just displayed in the UI.

---

### Step 7 — Grant Consent

**Action:** Check the checkbox, then click **"I Agree"**

**Expected assistant output:**
```
Thank you for providing consent. I can now proceed with the
credit pre-qualification. Please tell me your approximate
credit score or describe your credit (excellent, good, fair,
needs work).
```

**What happens behind the scenes:**
- A consent record is created with: consent_id, customer_id, timestamp, IP address, user agent, legal text version (v2026.1), and an expiration date (30 days from now).
- An audit log entry is written with event_type `soft_pull_consent`.
- The consent is type-specific: soft_pull consent does NOT authorize a hard_pull.

---

### Step 8a — Approved Outcome (Good Credit)

**You type:**
```
My credit score is around 720 and I have $5,000 down
```

**Expected assistant output:**
```
Great news! You're pre-qualified for the 2024 Toyota Camry!

Credit Tier: Prime
Monthly Payment: $XXX.XX/mo
APR: X.XX%
Term: 60 months
Principal: $XX,XXX.XX

Lender: [Lender Name]

This is a pre-qualification based on a soft credit pull.
Final terms may vary based on full credit application.
```

**Why this matters:** The credit decision is deterministic — it comes from the calculator and lender rules table, not from the LLM. The lender name and rule_id are cited for audit purposes.

---

### Step 8b — Declined Outcome (Low Credit) — For a Separate Demo Pass

To demonstrate a decline, start a new session and provide a low credit score:

**You type:**
```
My credit score is around 520
```

**Expected assistant output:**
```
Pre-Qualification Result for the [Vehicle]

Unfortunately, we're unable to pre-qualify you at this time.

Principal Reasons:
• Limited credit experience
• Delinquent past or present credit obligations with others

Bureau: Experian | Date: 2026-02-19

You have the right to obtain a free copy of your credit report.
If you have questions, please speak with our finance team.
```

**Why this matters:** The system never says "bad credit" or "low score." It provides specific Regulation B reason codes (e.g., C03, D02) with plain-language explanations. This is a federal requirement — generic reasons are forbidden by CFPB Circular 2023-03.

---

### Step 8c — Conditional Outcome (Borderline Credit) — For a Separate Demo Pass

For credit scores in the 600-649 range ("subprime" tier), the system may generate a **counter-offer** with adjusted terms:

**Expected assistant output:**
```
Conditional Pre-Qualification for the [Vehicle]

Credit Tier: Subprime

We can work with you! Here's what's needed:
• Increase down payment to $X,XXX
• Maximum term: 60 months

Counter-Offer:
Down payment: $X,XXX
APR: 12.99%
Term: 60 months
Monthly payment: $XXX.XX/mo

Would you like to proceed with these terms?
```

**Why this matters:** Instead of a flat denial, the system provides a realistic path forward. The counter-offer is calculated deterministically based on LTV requirements and tier-appropriate APR.

---

## 5. Scene 4: Deterministic Payment Estimates (11:00-14:00)

**What this scene demonstrates:** Payment calculations are performed by a deterministic calculator using Decimal arithmetic — the LLM never generates dollar amounts.

**Talking point for stakeholders:** "Every payment number you see comes from a math engine, not from the AI language model. The AI understands what you're asking and gathers the information, but the actual dollar amounts are calculated using the same kind of precision that a bank would use. Every quote also cites exactly which lender rule was used, so there's a complete audit trail."

---

### Step 9 — One-Shot Payment Estimate

If not continuing from the previous scene, start fresh:

**You type:**
```
What is the monthly payment on the first car? I have good credit and $5,000 down
```

**Expected assistant output:**
```
Payment Estimate

For the 2024 Toyota Camry you were looking at ($XX,XXX):

Monthly Payment: $XXX.XX/mo
APR: X.XX%
Term: 60 months
Down Payment: $5,000
Total Interest: $X,XXX.XX

Rule ID: RULE_XXX | Lender: [Lender Name]

DEMO ONLY: Synthetic lender rules for demonstration purposes.
Not a commitment to lend.
```

**What the UI shows:** A PaymentCard component displaying the estimate, plus the rule_id and lender citation.

**Why this matters:**
- The system resolved "the first car" to the first search result, resolved "good credit" to the Prime tier (FICO ~720), and extracted $5,000 as the down payment — all from one sentence.
- The payment was calculated using `Decimal` arithmetic (no floating-point drift).
- The response includes a `rule_id` and `lender_name` for audit traceability.
- The DEMO ONLY disclaimer is always present.

---

### Step 10 — Recalculation ("What If" Scenario)

**You type:**
```
What if I put $7,000 down instead?
```

**Expected assistant output:** A recalculated payment with a lower monthly amount, reflecting the higher down payment.

**You type:**
```
What if I do 48 months?
```

**Expected assistant output:** A recalculated payment with a higher monthly amount but shorter term.

**Why this matters:** The system maintains session context. It remembers which vehicle, credit tier, and previous parameters the user discussed, and only recalculates the changed variable.

---

## 6. Scene 5: Adverse Action and PDF Documents (14:00-17:00)

**What this scene demonstrates:** Regulation B-compliant adverse action notices with specific denial reason codes, counter-offers, and downloadable PDFs in English and Spanish.

**Talking point for stakeholders:** "When someone is declined, federal law requires specific reasons — not 'bad credit,' but reasons like 'Too many inquiries in the last 12 months.' Our system generates these notices with the correct codes, and can produce a formal PDF document in English or Spanish."

---

### Step 11 — Adverse Action PDF (English)

**Action:** Open a new browser tab and navigate to:
```
http://localhost:8000/api/documents/adverse-action/sample
```

**Expected output:** A downloadable PDF containing:
- **Notice ID:** DEMO-AA-001
- **Applicant Name:** Demo Customer
- **Decision Date:** Today's date
- **Bureau Source:** Experian
- **Specific Reason Codes:**
  - A01: "Too many inquiries in the last 12 months"
  - B02: "Amount owed on revolving accounts is too high"
  - C03: "Proportion of balances to credit limits is too high"
  - D04: "Length of time accounts have been established"
- **Counter-Offer:** 48 months, 12.99% APR, $785.50/mo, $5,000 down payment required
- **Legal Footer:** ECOA and FCRA rights statements

**Why this matters:** Every reason is a specific, auditable code — never a generic phrase. The notice also includes a counter-offer (a path forward for the customer) and the bureau source with score date.

---

### Step 12 — Adverse Action PDF (Spanish)

**Action:** Navigate to:
```
http://localhost:8000/api/documents/adverse-action/sample?language=es
```

**Expected output:** The same notice content, translated to Spanish.

**Why this matters:** Multi-language support for diverse customer populations.

---

### Step 13 — Offering Price PDF

**Action:** Navigate to:
```
http://localhost:8000/api/documents/offering-price/sample
```

**Expected output:** A downloadable PDF showing:
- Vehicle: 2024 Toyota Camry LE (VIN: 4T1BF1FK5EU123456)
- Base Vehicle Price: $28,995.00
- Documentation Fee: $85.00
- Pre-installed Add-ons: Nitrogen Tire Fill ($199), All-Weather Floor Mats ($249)
- **Total Offering Price: $29,528.00**

**Also available in Spanish:**
```
http://localhost:8000/api/documents/offering-price/sample?language=es
```

---

## 7. Scene 6: Architecture and Governance (17:00-20:00)

**What this scene demonstrates:** The system's multi-agent architecture, authorization model, PII protection, and audit integrity.

**Talking point for stakeholders:** "This isn't a single chatbot. It's six specialized AI agents working together, each with a specific job. One understands your question, one checks compliance rules, one handles payments, one handles credit decisions, and so on. There are also built-in protections for personal information and a tamper-proof audit trail."

---

### Step 14 — Health Endpoint (Agent Graph Visibility)

**Action:** Open a browser tab to:
```
http://localhost:8000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "database": "ok",
    "llm": "ok",
    "vector_store": "ok"
  },
  "agent_graph": "langgraph",
  "agent_nodes": [
    "conversationalist",
    "compliance_sentinel",
    "inventory_graph",
    "fin_calc_solver",
    "credit_officer",
    "responder"
  ],
  "authorization": {
    "mode": "local_rbac_fallback",
    "mode_reason": "OpenFGA client is not wired in this demo runtime; using local tuple-backed RBAC/ReBAC fallback.",
    "openfga_configured": false,
    "local_tuple_count": [N]
  }
}
```

**What to point out:**
- **6 named agents** orchestrated by LangGraph StateGraph:
  - **Conversationalist:** Understands the user's question and extracts intent
  - **Compliance Sentinel:** Enforces SB 766, CARS Act add-on rules
  - **Inventory Graph:** Searches and filters vehicle inventory
  - **Fin_Calc_Solver:** Deterministic payment calculator (never the LLM)
  - **Credit Officer:** Handles FCRA consent and credit decisions
  - **Responder:** Formats the final natural language response
- **Authorization mode:** Shows whether OpenFGA (enterprise-grade) or local RBAC fallback is active. The local fallback uses the same relationship-based access control (ReBAC) model loaded from `openfga/tuples.json`.

---

### Step 15 — PII Scrubbing (Explain, Don't Demo Directly)

**Talking point:** "Before any customer data is sent to the language model, a PII scrubber strips sensitive fields. Social Security numbers become `***-**-6789`, dates of birth keep only the year and month (for age checks), and email addresses are masked. The scrubbing level depends on the user's clearance level — a finance manager sees more than a sales rep."

**Evidence (from backend tests):**
- `123-45-6789` becomes `***-**-6789` (last 4 preserved)
- `1985-04-12` becomes `1985-04-01` (day zeroed, year/month preserved for age verification)
- `john.doe@example.com` becomes `j****@example.com` (domain preserved)
- `555-123-4567` becomes `***-***-4567` (last 4 preserved)
- Three clearance levels: HIGH (full access), MEDIUM (SSN/DOB masked), LOW (all PII masked)
- LLM context always uses LOW clearance — the AI never sees raw SSN or account numbers

---

### Step 16 — Audit Trail Integrity (Explain, Don't Demo Directly)

**Talking point:** "Every compliance event — every disclosure, every consent, every credit decision — is logged with a SHA-256 hash of the payload. If anyone tries to alter a record after the fact, the hash won't match and the tampering is detected. The audit entries also form a chain, similar in concept to a blockchain, where each entry references the previous one."

**Evidence (from backend tests):**
- Each audit entry contains: transaction_id (UUID), timestamp (ISO 8601), actor, event_type, payload_hash (64-character SHA-256 hex), and regulatory_flags
- Hash chain verification: if any entry is modified, `verify_chain()` returns False
- Regulatory flags include: `sb766_disclosure_verified`, `adverse_action_generated`, `reg_b_compliant`, `cars_act_validated`

---

### Step 17 — Authorization Model (Explain, Don't Demo Directly)

**Talking point:** "The system uses relationship-based access control. A sales rep can only see deals they own. A finance manager can edit deals at their dealership but not at another dealership. A compliance officer can see sensitive audit logs that others cannot. In production, this would run on OpenFGA (an open-source authorization engine). For this demo, we simulate the same rules locally."

**Evidence (from backend tests):**
- Deal owner can edit; finance manager at same dealership can edit; sales rep at different store cannot
- Cross-store isolation: Store A member cannot view Store B deals
- General manager has auditor access (read-only audit trail) but not editor by default
- Compliance officer can view sensitive logs; regular members cannot
- Customer owns their own profile (can_view_pii on their own data)

---

### Step 18 — Explorer, Dashboard, and Audit Views

**Action:** Click through the sidebar navigation tabs.

| View | What It Shows | Status |
|------|---------------|--------|
| **Explorer** | Data lake browser (Lakes → Zones → Assets) | Simulated with mock data (frontend-only). Shows the concept of governed data zones. |
| **Dashboard** | SRE observability (latency, traffic, errors, saturation charts) | Simulated with randomly generated mock data. Illustrates where real monitoring would appear. |
| **Audit Logs** | Compliance audit trail table | Simulated with hardcoded sample entries. The real audit logging happens in the backend database (audit_logs table). |
| **Chat** | The AI assistant | **Live** — connected to the real backend. |

---

## 8. Full Chatbot Conversation Script

This is a complete, copy-paste-ready conversation covering all chatbot abilities. Each step includes the exact prompt, expected output, and what to point out.

---

### Conversation A: Complete Happy Path (Scenes 1-4)

| # | You Type | Expected Output Summary | What to Point Out |
|---|----------|------------------------|-------------------|
| A1 | `Show me Toyota Camry sedans under $30,000` | List of matching vehicles with cards | Natural language parsing: make + model + body style + price filter |
| A2 | `Tell me about #3` | Full vehicle details | Reference resolution: "#3" → third search result |
| A3 | `How much is the monthly payment?` | SB 766 offering price disclosure (NOT a payment) | Compliance Sentinel blocked the payment and showed offering price first |
| A4 | `Yes, I'd like to see financing options` | Prompts for credit score and down payment | State machine: system knows you confirmed and asks for missing info |
| A5 | `I have good credit, score around 720, and $3,000 down` | Payment estimate with monthly amount, APR, term, rule_id, lender | Deterministic calculator; LLM did not generate the dollar amount |
| A6 | `What if I put $5,000 down instead?` | Updated lower monthly payment | Session context: remembers vehicle, credit, and recalculates |
| A7 | `Can I get approved?` | FCRA consent card appears in UI | Consent required before any credit evaluation |
| A8 | *(Click checkbox, then "I Agree")* | Consent recorded; asks for credit info | IP, timestamp, legal text version logged |
| A9 | `My credit score is 720` | Pre-qualified: approved terms shown | Credit Officer evaluated with deterministic rules |
| A10 | `Show me similar vehicles` | Vector similarity results with match percentages | ChromaDB semantic search, not keyword matching |

---

### Conversation B: Edge Cases and Guardrails

| # | You Type | Expected Output Summary | What to Point Out |
|---|----------|------------------------|-------------------|
| B1 | `Show me Lamborghinis under $10,000` | "I couldn't find any vehicles matching those criteria. Try broadening your search." | Graceful empty result handling |
| B2 | `Hello!` | Greeting with capability overview | Greeting intent recognized |
| B3 | `What's the weather today?` | "That's outside what I can help with." Lists available capabilities. | Out-of-scope guardrail |
| B4 | `Help` | Clarification: A) Inventory, B) Similar Vehicles, C) Payments | Disambiguation when intent is unclear |
| B5 | `A` | Routes to inventory search | Clarification response mapping |
| B6 | `Tell me about the first one` | Details of first vehicle from search | Ordinal reference resolution |
| B7 | `Tell me about the last one` | Details of last vehicle from search | "last" reference resolution |
| B8 | `What about that one?` | Details of the currently focused vehicle | Pronoun reference ("that one" → current_vehicle) |
| B9 | `Show me SUVs from 20k to 35k` | SUVs in $20,000-$35,000 range | "k" notation parsing |
| B10 | `Show me SUVs between $35,000 and $20,000` | Same results as B9 (reversed range normalized) | Reversed price range correction |

---

### Conversation C: One-Shot Payment (No Multi-Turn)

| # | You Type | Expected Output Summary | What to Point Out |
|---|----------|------------------------|-------------------|
| C1 | `Show me Honda vehicles` | List of Honda vehicles | Search by make |
| C2 | `What's the monthly payment on #2 with 720 credit and $3,000 down?` | Offering price disclosure first, then prompts for payment confirmation (or provides payment if disclosure already done) | One-shot: all info in one message, but SB 766 still enforced |

---

## 9. Compliance Matrix

| Compliance Topic | Where Shown in Demo | Expected Output Evidence | Why Output Is Compliant | Official Source | Plain-Language Explanation |
|---|---|---|---|---|---|
| **California SB 766 — Offering Price Disclosure** | Scene 2, Step 5 | "Before we get to payments, the Offering Price for this [Vehicle] is $XX,XXX" with itemized base price + doc fee, and "Government taxes and registration fees are extra" | The total cash price is disclosed with an itemized breakdown before any financing/payment discussion, exactly as SB 766 requires. Government charges are explicitly excluded. | [CA SB 766 (2023-2024 Session)](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB766) | Before a dealer can talk about monthly payments, the law says they must first tell you the full cash price of the car, broken down so you can see each charge. Our system does this automatically and won't let anyone skip it. |
| **FCRA — Written Consent Before Credit Inquiry** | Scene 3, Steps 6-7 | SoftPullCard UI with FCRA consent language, checkbox, "I Agree" button. Consent logged with consent_id, timestamp, IP, legal text version, 30-day expiration. | Written instructions captured per FCRA §604(a)(2). Consent is time-limited, type-specific (soft pull ≠ hard pull), and logged with audit metadata. | [15 U.S.C. § 1681b — Permissible purposes of consumer reports (FCRA)](https://www.law.cornell.edu/uscode/text/15/1681b) | Federal law says you must give written permission before anyone checks your credit. Our system shows the consent form, records your agreement with a timestamp and IP address, and won't proceed without it. The consent expires after 30 days. |
| **Regulation B (ECOA) — Specific Adverse Action Reasons** | Scene 5, Steps 11-12; Scene 3, Step 8b | Reason codes A01, B02, C03, D04 with specific text (e.g., "Too many inquiries in the last 12 months"). Never "bad credit" or "credit score." Max 4 reasons per notice. Bureau source and score date included. | Reg B §1002.9 requires specific, principal reasons for denial. CFPB Circular 2023-03 explicitly prohibits generic reasons. System enforces max 4 reasons, validates no forbidden phrases, and includes bureau source/date. | [12 CFR § 1002.9 — Notifications (Reg B)](https://www.ecfr.gov/current/title-12/chapter-X/part-1002/section-1002.9) and [CFPB Circular 2023-03](https://www.consumerfinance.gov/compliance/circulars/circular-2023-03-adverse-action-notification-requirements-and-the-proper-use-of-the-cfpbs-sample-forms-provided-in-regulation-b/) | If a lender turns you down, they must tell you exactly why — not just "bad credit." Our system gives up to four specific reasons (like "too many recent credit inquiries") with the correct regulatory codes, plus which credit bureau was used and when. |
| **ECOA — Counter-Offer on Conditional Denial** | Scene 3, Step 8c; Scene 5, PDF counter-offer section | Counter-offer with adjusted down payment, APR, term, and monthly payment. "We can approve you with a down payment of $X,XXX at Y% APR for Z months." | Reg B allows creditors to provide counter-offers with alternative terms. The system generates realistic alternative terms when the initial request doesn't qualify. | [12 CFR § 1002.9(a)(1) — Notification of action taken (Reg B)](https://www.ecfr.gov/current/title-12/chapter-X/part-1002/section-1002.9) | If you don't qualify for the exact terms you asked for, the system offers an alternative (like a higher down payment or shorter term) instead of just saying "no." |
| **Deterministic Payment Calculation — LLM Guardrail** | Scene 4, Steps 9-10 | Monthly payment with cited rule_id and lender_name. DEMO ONLY disclaimer always present. | The LLM classifies intent and formats responses but never generates payment amounts. All dollar values come from `calculator.py` using Decimal arithmetic. Every quote traces to a specific lender rule. | N/A (internal engineering control; aligns with [CFPB guidance on AI in lending](https://www.consumerfinance.gov/about-us/blog/chatbots-in-consumer-finance/) regarding accuracy and explainability) | The AI understands your question, but a separate math engine calculates the actual dollar amounts. This prevents the AI from making up numbers. Every quote shows which lender rule was used, so it can be verified. |
| **PII Scrubbing — Data Minimization** | Scene 6, Step 15 (explained) | SSN → `***-**-6789`, DOB → `1985-04-01`, Email → `j****@example.com`. Three clearance levels. LLM context always uses LOW clearance. | PII is masked before reaching the LLM, following data minimization principles. Clearance-based access control ensures users only see data appropriate to their role. | [FTC Act § 5 — Unfair or Deceptive Acts](https://www.ftc.gov/legal-library/browse/statutes/federal-trade-commission-act) and [GLBA Safeguards Rule (16 CFR Part 314)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314) — Note: these are the closest applicable frameworks for AI data minimization in auto lending; there is no single regulation specifically addressing LLM PII scrubbing. | Personal information like Social Security numbers is hidden before the AI sees it. The AI only gets the minimum data it needs to do its job. A sales rep sees less customer data than a finance manager. |
| **Audit Trail Integrity — Tamper Evidence** | Scene 6, Step 16 (explained) | SHA-256 payload hashes on every audit entry. Hash chain verification. Regulatory flags (sb766_disclosure_verified, reg_b_compliant, etc.). | Cryptographic hashing provides non-repudiation and tamper detection. If any record is altered, the hash chain breaks and verification fails. | [GLBA § 501(b) — Safeguarding Customer Information](https://www.law.cornell.edu/uscode/text/15/6801) and general audit trail requirements per [SOX § 802](https://www.law.cornell.edu/uscode/text/18/1519) — Note: SOX applies to public companies; cited here as the standard for financial record integrity. | Every action the system takes is recorded with a digital fingerprint (a hash). If anyone changes a record after the fact, the system can detect it. This is similar to how a blockchain works — each record links to the previous one. |
| **CARS Act — Add-On Validation** | Compliance Sentinel service (code-level) | Blocks oil change add-on for electric vehicles. Blocks add-ons without documented benefit statements. | Per CARS Act, add-ons must provide documented benefit for the specific vehicle. System validates before allowing add-on. | [FTC CARS Rule (16 CFR Part 463)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-463) — Note: The CARS Rule was vacated by the Fifth Circuit in January 2025 but the compliance logic remains in the codebase as a best-practice demonstration. | The system checks whether an add-on product actually makes sense for the vehicle. For example, it won't let you sell an oil change package on an electric car. |
| **Cross-Store Data Isolation** | Scene 6, Step 17 (explained) | Authorization check: Store A member denied access to Store B deal. | Role-based and relationship-based access control prevents cross-dealership data leakage. | [GLBA Safeguards Rule (16 CFR Part 314)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314) and [FTC Privacy Rule (16 CFR Part 313)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-313) | An employee at one dealership cannot see customer deals or data from a different dealership. The system checks who you are and what you're allowed to see before showing any information. |
| **Bilingual Document Support (EN/ES)** | Scene 5, Steps 11-13 | PDFs available in English and Spanish via `?language=es` parameter | Supports diverse customer populations with translated compliance documents. | [Executive Order 13166 — Improving Access to Services for Persons with Limited English Proficiency](https://www.justice.gov/crt/executive-order-13166) — Note: EO 13166 applies to federal agencies and recipients of federal financial assistance; cited as the policy framework for language access. | Important documents like denial notices are available in Spanish, so customers who speak Spanish can understand their rights and the reasons for any decision. |

---

## 10. Stakeholder Summary

### What This System Does (Non-Technical)

Mini-Lakebed is a demonstration of how artificial intelligence can help automotive dealerships serve customers while following federal and state laws automatically.

**For the customer:** You can ask questions in plain English — "Show me SUVs under $30,000" or "What's my monthly payment?" — and get accurate, transparent answers. The system shows you the full price before talking about monthly payments, asks your permission before checking credit, and gives you specific reasons if financing isn't available for the terms you requested.

**For the dealership:** The system prevents common compliance mistakes. It won't skip the offering price disclosure, won't pull credit without consent, and won't give vague denial reasons. Every action is logged with a tamper-proof audit trail that a regulator could review.

**For regulators and oversight:** Every compliance event is logged with a cryptographic hash. Disclosure events, consent records, and credit decisions all have audit entries that can be verified for integrity. The system enforces rules in code, not in training — meaning the rules can't be "talked around" by clever prompts.

### What Makes This Different from a Regular Chatbot

1. **Six specialized agents** work together instead of one general-purpose AI. Each agent has a specific job and specific rules.
2. **The AI never generates dollar amounts.** A separate, deterministic calculator does all the math.
3. **Compliance is enforced in code, not in prompts.** The Compliance Sentinel agent blocks non-compliant actions before they happen.
4. **Every action is auditable.** SHA-256 hashes, timestamps, and regulatory flags create a verifiable record.
5. **Personal information is protected.** The PII scrubber ensures the AI never sees raw Social Security numbers or account numbers.

---

## 11. Demo Limitations: What Is Mocked vs. Live

| Feature | Status | Details |
|---------|--------|---------|
| **Chat AI assistant** | **Live** | Real LLM (Ollama llama3.1:8b) with regex fallback. Connected to real backend. |
| **Inventory database** | **Live (synthetic data)** | 1,200 vehicles in SQLite. Data is seeded by script — not real dealer inventory. |
| **Payment calculator** | **Live (synthetic rules)** | Deterministic calculator is real code. Lender rules and APRs are made up for demo purposes. |
| **FCRA consent flow** | **Live** | Consent is recorded in the database with timestamp, IP, and expiration. Not connected to any real credit bureau. |
| **Credit pre-qualification** | **Live (synthetic decisions)** | Credit tier assignment and decision logic are real code. FICO scores and credit data are user-provided demo values — no real credit pull occurs. |
| **Adverse action notices** | **Live (sample data)** | Reason codes and counter-offer logic are real. The sample PDFs use hardcoded demo data. |
| **PDF generation** | **Live** | Real server-side PDF generation (text-based). Reports use the `reportlab` library if installed, otherwise a built-in text generator. |
| **SB 766 compliance enforcement** | **Live** | The Compliance Sentinel actively blocks payment quotes without prior offering price disclosure. |
| **PII scrubber** | **Live** | Real middleware that scrubs data before LLM context. Tested with 28 unit tests. |
| **Audit trail with hashing** | **Live** | Real SHA-256 hashing and chain verification. Records written to SQLite audit_logs table. |
| **Authorization (RBAC)** | **Live (local fallback)** | Real role/relationship checks using in-memory tuple store. OpenFGA server is not connected in demo mode. |
| **Vector search (similar vehicles)** | **Live** | Real ChromaDB semantic search with nomic-embed-text embeddings. Falls back to SQL if vector search times out. |
| **Explorer view (Lakes/Zones/Assets)** | **Mock** | Frontend-only with hardcoded mock data. Demonstrates the data governance UI concept. |
| **Dashboard (Observability)** | **Mock** | Randomly generated charts. No real metrics collection. Demonstrates where monitoring would appear. |
| **Audit Logs view** | **Mock** | Hardcoded sample entries in the frontend. The real audit logging is in the backend database and is not yet surfaced in this UI. |
| **Bilingual UI** | **Partial** | PDF documents support EN/ES. The chat interface is English-only. i18n files (en.json, es.json) exist for future full localization. |
| **Credit bureau integration** | **Not connected** | No real Experian/Equifax/TransUnion integration. Bureau source is always "Experian" in demo output. |
| **OpenFGA server** | **Not connected** | Authorization model and tuples are defined but the OpenFGA server is not running. The local RBAC fallback implements the same logic. |
| **MongoDB** | **Not connected in basic demo** | README lists MongoDB as a component, but the core demo runs on SQLite only. |

---

## 12. Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python executable not found" when running start script | Create a venv: `python3 -m venv venv` in the project root, or set `PYTHON_BIN=$(which python3)` |
| Empty vehicle list / no search results | Run `python -m scripts.seed_data --vehicles 1200` |
| Ollama errors / slow first response | Run `ollama serve` and `ollama pull llama3.1:8b`. Or use `DEMO_FORCE_FALLBACK=1` for regex fallback. |
| "No matching rule" on payment estimate | Check inputs: FICO must be 650+, term must be 48/60/72 months, LTV must be ≤ 1.20 |
| Frontend can't connect to backend | Verify backend is running on port 8000. Check browser console for CORS errors. |
| PDF endpoints return 404 | Use `/api/documents/adverse-action/sample` (not `/pdf`). The `/pdf` endpoints require POST with a JSON body. |
| Consent card doesn't appear | Make sure a vehicle is selected first (the pre-qualification flow requires a vehicle in context). |
| Payment shows wrong vehicle | Session context may have stale data. Start a new chat session by refreshing the page. |

---

## Test Coverage Reference

This demo is backed by **129 automated tests** across 10 test files:

| Domain | Test Count | File |
|--------|-----------|------|
| SB 766 Disclosure | 5 | `backend/tests/test_sb766_disclosure.py` |
| FCRA Consent | 17 | `backend/tests/test_fcra_consent.py` |
| Regulation B Adverse Action | 16 | `backend/tests/test_adverse_action.py` |
| Authorization (RBAC/ReBAC) | 12 | `backend/tests/test_authorization.py` |
| PII Scrubbing | 28 | `backend/tests/test_pii_scrubber.py` |
| Audit Trail Integrity | 24 | `backend/tests/test_audit_integrity.py` |
| Inventory Search (E2E) | 8 | `frontend/e2e/inventory-search.spec.ts` |
| Vehicle Selection (E2E) | 6 | `frontend/e2e/vehicle-selection.spec.ts` |
| Payment Estimates (E2E) | 8 | `frontend/e2e/payment-estimate.spec.ts` |
| Pre-Qualification (E2E) | 5 | `frontend/e2e/prequalification.spec.ts` |

To run backend tests: `cd backend && pytest tests/ -v`
To run frontend E2E tests: `cd frontend && npx playwright test`
