# Project Gap Report: Mini-Lakebed MVP

**Generated:** 2026-01-23
**Spec Sources:** `01_general_proposal.md`, `02_strategic_blueprint.md`, `03_implementation_dummy_data_plan.md`
**Branch:** `chore/minilakebed-hardening`

---

## Executive Summary

The current implementation provides a working MVP foundation with basic chat, inventory search, payment calculation, and session management. However, significant gaps exist between the spec-defined "Neuro-Symbolic Architecture" and the current implementation, particularly in:

- **Agent Architecture:** 2 of 5 agents partially implemented, 3 missing entirely
- **Data Models:** 1 of 4 canonical entities present, 1 partial, 2 missing
- **Compliance Features:** Core SB 766 / FCRA / Reg B features not implemented
- **Governance:** No OpenFGA authorization or PII scrubbing

---

## 1. Agent Taxonomy

| Agent | Spec Requirement | Current Status | Gap Details |
|-------|------------------|----------------|-------------|
| **Conversationalist** | LLM for intent classification, NLG, empathy, context management | **PARTIAL** | `llm.py` + `chat.py` provide basic intent classification with Ollama fallback. Missing: sophisticated context management, empathy detection, multi-turn reasoning |
| **Inventory_Graph** | Vector DB + Knowledge Graph (GraphRAG) for semantic vehicle matching | **PARTIAL** | `vector_store.py` implements ChromaDB for semantic search. Missing: Knowledge Graph, feature-to-VIN traversal, "safe car for kids" → ISOFIX mapping |
| **Fin_Calc_Solver** | SMT Solver (Z3/CVXPY) for penny-perfect deal structuring | **PARTIAL** | `calculator.py` implements deterministic amortization. Missing: SMT solver integration, constraint optimization, state-specific tax rules, day-count conventions |
| **Compliance_Sentinel** | BERT classifier + Rego rules for regulatory scanning | **MISSING** | No adversarial prompt detection, no SB 766 disclosure enforcement, no valueless add-on blocking |
| **Credit_Officer** | Decision engine (XGBoost) for credit tiering + adverse action | **MISSING** | No soft-pull integration, no FICO-to-tier mapping, no Reg B adverse action generation |

### Next Files/Tests for Agents

| Priority | File to Create | Purpose |
|----------|---------------|---------|
| 1 | `backend/app/services/compliance_sentinel.py` | SB 766 offering price enforcement, add-on validation |
| 2 | `backend/app/services/credit_officer.py` | Credit tier assignment, adverse action reason codes |
| 3 | `backend/app/services/knowledge_graph.py` | Feature-to-vehicle mapping for semantic queries |
| 4 | `backend/tests/test_compliance_sentinel.py` | Test SB 766 disclosure before payment quotes |
| 5 | `backend/tests/test_adverse_action.py` | Test Reg B reason code generation |

---

## 2. Canonical Data Models

| Entity | Spec Reference | Current Status | Gap Details |
|--------|---------------|----------------|-------------|
| **CustomerProfile** | `03_implementation_dummy_data_plan.md` §1.1 | **MISSING** | No customer table. Spec requires: UUID, identity (SSN token), residence, employment, `fcra_consent_log[]`, `pii_clearance_level` |
| **InventoryUnit** | `03_implementation_dummy_data_plan.md` §1.2 | **PARTIAL** | `inventory` table exists. Missing: `sb766_offering_price` (distinct from `price`), `add_ons[]` with `benefit_statement` and `compliance_check_passed` |
| **DealJacket** | `03_implementation_dummy_data_plan.md` §1.3 | **MISSING** | No deal structure table. Spec requires: `financial_structure`, `tax_calculation` (with `taxable_basis`, `rule_applied`), `trade_in` (with negative equity), `lending_terms` (with `days_basis`), `audit_trail[]` |
| **ComplianceLog** | `03_implementation_dummy_data_plan.md` §1.4 | **PARTIAL** | `audit_logs` table exists but simplified. Missing: `credit_data_used`, `denial_reasons[]` (Reg B codes), `notice_details`, `payload_hash` for tamper evidence |

### Current Schema vs Spec Schema

**inventory table:**
```
PRESENT: id, vin, make, model, year, trim, body_style, price, msrp, status
MISSING: sb766_offering_price, add_ons (JSON array), location.store_id
```

**lender_rules table:**
```
PRESENT: rule_id, lender_name, credit_tier, min/max_fico, base_apr, max_ltv
MISSING: days_basis (calc_method), dealer_reserve_cap, stips_required[]
```

**audit_logs table:**
```
PRESENT: session_id, timestamp, action, request_params, rule_id
MISSING: payload_hash (SHA-256), regulatory_flags{}, actor (agent attribution)
```

### Next Files/Tests for Data Models

| Priority | File to Create/Modify | Purpose |
|----------|----------------------|---------|
| 1 | `data/schema.sql` | Add `customers`, `deals`, `compliance_logs` tables |
| 2 | `backend/app/models/schemas.py` | Add `CustomerProfile`, `DealJacket`, `ComplianceLog` Pydantic models |
| 3 | `data/migrations/001_add_sb766_fields.sql` | Add `sb766_offering_price`, `add_ons` to inventory |
| 4 | `backend/tests/test_data_models.py` | Validate schema compliance with spec |

---

## 3. User Stories (12 Total)

### Theme A: Inventory & Pricing Transparency (SB 766)

| Story | Title | Current Status | Gap |
|-------|-------|----------------|-----|
| US-1 | Total Price Disclosure | **MISSING** | No enforcement of "Offering Price before payment quote" |
| US-2 | Valueless Add-on Prevention | **MISSING** | No add-on validation against vehicle features |
| US-3 | Penny-Perfect Tax Calculation | **PARTIAL** | No tax calculation; calculator uses price directly without tax |

### Theme B: Credit & Identity (FCRA, GLBA)

| Story | Title | Current Status | Gap |
|-------|-------|----------------|-----|
| US-4 | Soft-Pull Consent Handshake | **MISSING** | No consent UI card, no FCRA logging |
| US-5 | Identity Verification (Red Flags) | **MISSING** | No address mismatch detection |
| US-6 | NPI Data Redaction | **MISSING** | No PII scrubbing before LLM context |

### Theme C: Deal Structuring (ECOA/Reg B)

| Story | Title | Current Status | Gap |
|-------|-------|----------------|-----|
| US-7 | Penny-Perfect Payment Solution | **PARTIAL** | Calculator exists but lacks tax, trade-in equity, day-count methods |
| US-8 | Adverse Action Explanation | **MISSING** | No Reg B reason code mapping |
| US-9 | Counter-Offer Generation | **MISSING** | No conditional approval handling |

### Theme D: Auditing (GLBA)

| Story | Title | Current Status | Gap |
|-------|-------|----------------|-----|
| US-10 | Immutable Audit Log | **PARTIAL** | Audit table exists but no hash chain/Merkle tree |
| US-11 | 3-Day Right to Cancel | **MISSING** | No CA cancellation option disclosure |
| US-12 | Multi-Lingual Disclosure | **MISSING** | No language detection or Spanish templates |

### Next Files/Tests for User Stories

| Priority | File | Story Coverage |
|----------|------|----------------|
| 1 | `backend/app/routers/disclosure.py` | US-1, US-11 |
| 2 | `backend/app/services/tax_calculator.py` | US-3, US-7 |
| 3 | `backend/app/services/consent_manager.py` | US-4 |
| 4 | `backend/app/services/adverse_action.py` | US-8, US-9 |
| 5 | `backend/tests/test_user_stories.py` | BDD tests for all 12 stories |

---

## 4. Deterministic Math Specifications

| Requirement | Spec Reference | Current Status | Gap |
|-------------|---------------|----------------|-----|
| **30/360 Day Count** | §4.1 Method A | **PRESENT** | `calculator.py` uses `APR/12` (equivalent) |
| **Actual/365 Simple Interest** | §4.1 Method B | **MISSING** | Not implemented |
| **365/360 Bank Method** | §4.1 Method C | **MISSING** | Not implemented |
| **CA Trade-In Tax Rule** | §4.2 | **MISSING** | No state-specific tax logic |
| **Arbitrary Precision** | §4 intro | **PARTIAL** | Uses `float`, should use `Decimal` |

### Next Files for Math

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `backend/app/services/day_count.py` | Implement all 3 interest calculation methods |
| 2 | `backend/app/services/tax_calculator.py` | State-specific tax basis rules |
| 3 | `backend/tests/test_penny_perfect.py` | Verify $35k/5%/60mo = $660.49 exactly |

---

## 5. Governance & Security

| Requirement | Spec Reference | Current Status | Gap |
|-------------|---------------|----------------|-----|
| **OpenFGA Authorization** | `02_strategic_blueprint.md` §3.3 | **MISSING** | No FGA integration |
| **ReBAC Model** | Deal → Dealership → User relationships | **MISSING** | No authorization model DSL |
| **PII Scrubbing** | SSN masking before LLM context | **MISSING** | No middleware interceptor |
| **Cryptographic Audit Trail** | SHA-256 payload hashing | **MISSING** | No `payload_hash` field |

### Next Files for Governance

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `backend/app/middleware/pii_scrubber.py` | Redact SSN, DOB before LLM |
| 2 | `backend/app/services/authorization.py` | OpenFGA check wrapper |
| 3 | `openfga/model.fga` | Authorization DSL from spec |
| 4 | `backend/tests/test_authorization.py` | Cross-store isolation tests |

---

## 6. Dummy Data Completeness

| Dataset | Spec Volume | Current Status | Gap |
|---------|-------------|----------------|-----|
| **Leads/Customers** | 5,000 | **MISSING** | No customer data generation |
| **Inventory** | 1,000-2,500 | **PARTIAL** | `seed_data.py` exists; verify count |
| **Lender Programs** | 50 (5 lenders × 5 tiers) | **PARTIAL** | Likely fewer; check `lender_rules` count |
| **Tax Jurisdictions** | 100 (top metros) | **MISSING** | No `tax_rates.csv` |
| **Adverse Action Codes** | 25 (Reg B codes) | **MISSING** | No `adverse_action_codes.json` |
| **Compliance Logs** | 1,000 pre-filled | **MISSING** | No historical audit data |

### Next Files for Dummy Data

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `data/reference/tax_rates.csv` | 100 jurisdictions with CA/AZ rules |
| 2 | `data/reference/adverse_action_codes.json` | Reg B reason codes |
| 3 | `scripts/generate_customers.py` | 5,000 synthetic leads |
| 4 | `scripts/generate_lender_programs.py` | Expand to 50 programs |
| 5 | `data/reference/lender_programs.json` | Full spec schema with `days_basis` |

---

## 7. Rate Sheet & Audit Log JSON Schemas

### Rate Sheet Schema

| Field | Spec Requirement | Current Status |
|-------|------------------|----------------|
| `lender_id` | enum: Ally, Chase, CapitalOne | **PARTIAL** - `lender_name` TEXT |
| `effective_date` | date format | **PRESENT** |
| `programs[].tier` | enum: S, A, B, C, D | **PARTIAL** - `credit_tier` uses different names |
| `programs[].rates[].term` | enum: 36, 48, 60, 72, 84 | **PARTIAL** - uses min/max range |
| `programs[].rates[].dealer_reserve_cap` | max 2.5 | **MISSING** |
| `programs[].stips_required` | array: poi, por, references | **MISSING** |

### Audit Log Schema

| Field | Spec Requirement | Current Status |
|-------|------------------|----------------|
| `transaction_id` | UUID | **MISSING** - uses INTEGER id |
| `actor` | enum: user, agent:conversationalist, etc. | **MISSING** |
| `event_type` | enum: rate_inquiry, soft_pull_consent, etc. | **PARTIAL** - `action` is freeform |
| `payload_hash` | SHA-256 hex | **MISSING** |
| `context_snapshot.active_rate_sheet_id` | reference | **MISSING** |
| `regulatory_flags.fcra_compliant` | boolean | **MISSING** |
| `regulatory_flags.sb766_disclosure_verified` | boolean | **MISSING** |

---

## 8. Frontend Gaps

| Feature | Spec Reference | Current Status | Gap |
|---------|---------------|----------------|-----|
| **Soft-Pull Consent UI Card** | US-4 | **MISSING** | No distinct consent component |
| **Offering Price Display** | US-1 (Demo Scene 1) | **PARTIAL** | Shows price but not SB 766 formatted |
| **Adverse Action PDF Download** | US-8 (Demo Scene 4) | **MISSING** | No PDF generation |
| **Multi-Language Toggle** | US-12 | **MISSING** | English only |
| **Deal Structure Table** | Demo Scene 3 | **MISSING** | No interactive payment breakdown |

### Next Files for Frontend

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `frontend/src/components/Consent/SoftPullCard.tsx` | FCRA consent UI |
| 2 | `frontend/src/components/Deal/PaymentBreakdown.tsx` | Interactive deal table |
| 3 | `frontend/src/components/Common/OfferingPrice.tsx` | SB 766 compliant display |

---

## 9. Test Coverage Gaps

**Current Tests:**
- `test_session_context.py` - Session state management
- `test_session_bdd.py` - BDD scenarios (3 failing)

**Missing Test Categories:**

| Category | Test File Needed | Coverage |
|----------|-----------------|----------|
| Compliance | `test_sb766_disclosure.py` | Offering price before payment |
| Compliance | `test_valueless_addons.py` | Block invalid add-ons |
| Credit | `test_adverse_action.py` | Reg B reason codes |
| Credit | `test_fcra_consent.py` | Consent logging |
| Math | `test_day_count_methods.py` | All 3 interest methods |
| Math | `test_tax_calculation.py` | CA vs AZ rules |
| Security | `test_pii_scrubbing.py` | SSN redaction |
| Security | `test_authorization.py` | OpenFGA checks |

---

## 10. Priority Implementation Roadmap

### Phase 1: Data Foundation (Critical)
1. Extend `data/schema.sql` with `customers`, `deals`, `compliance_logs`
2. Add `sb766_offering_price` and `add_ons` to inventory
3. Create `data/reference/tax_rates.csv` (CA, AZ focus)
4. Create `data/reference/adverse_action_codes.json`

### Phase 2: Core Compliance (High)
1. Implement `compliance_sentinel.py` - SB 766 enforcement
2. Implement `adverse_action.py` - Reg B reason codes
3. Add `payload_hash` to audit logs
4. Create `test_sb766_disclosure.py`

### Phase 3: Credit Flow (High)
1. Implement `credit_officer.py` - tier assignment
2. Create `consent_manager.py` - FCRA logging
3. Add `SoftPullCard.tsx` to frontend
4. Create `test_fcra_consent.py`

### Phase 4: Math Precision (Medium)
1. Implement `day_count.py` - all 3 methods
2. Implement `tax_calculator.py` - state rules
3. Migrate calculator to `Decimal` precision
4. Create `test_penny_perfect.py`

### Phase 5: Governance (Medium)
1. Create `openfga/model.fga`
2. Implement `pii_scrubber.py` middleware
3. Implement `authorization.py` checks
4. Create `test_authorization.py`

### Phase 6: Demo Polish (Lower)
1. Frontend `PaymentBreakdown.tsx`
2. PDF generation for adverse action
3. Spanish language templates
4. Pre-fill 1,000 compliance logs

---

## Appendix: File Mapping Summary

| Spec Artifact | Current File | Status |
|---------------|-------------|--------|
| Conversationalist Agent | `backend/app/routers/chat.py`, `backend/app/services/llm.py` | PARTIAL |
| Inventory_Graph Agent | `backend/app/services/vector_store.py` | PARTIAL |
| Fin_Calc_Solver Agent | `backend/app/services/calculator.py` | PARTIAL |
| Compliance_Sentinel Agent | (none) | MISSING |
| Credit_Officer Agent | (none) | MISSING |
| CustomerProfile Model | (none) | MISSING |
| InventoryUnit Model | `data/schema.sql:inventory` | PARTIAL |
| DealJacket Model | (none) | MISSING |
| ComplianceLog Model | `data/schema.sql:audit_logs` | PARTIAL |
| OpenFGA Model | (none) | MISSING |
| Rate Sheet Schema | `data/schema.sql:lender_rules` | PARTIAL |
| Audit Log Schema | `data/schema.sql:audit_logs` | PARTIAL |
| Tax Jurisdictions | (none) | MISSING |
| Adverse Action Codes | (none) | MISSING |
