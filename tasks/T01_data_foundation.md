# T01: Data Foundation

**Priority:** Critical
**Status:** Not Started
**Depends On:** None
**Blocked By:** None

---

## Objective

Extend the database schema to support the Canonical Domain Data Model (CDDM) defined in specs. This is the foundation for all subsequent compliance and governance features.

---

## Spec References

| Spec File | Section | Requirement |
|-----------|---------|-------------|
| `03_implementation_dummy_data_plan.md` | §1. Canonical Domain Data Model | Define CustomerProfile, InventoryUnit, DealJacket, ComplianceLog |
| `03_implementation_dummy_data_plan.md` | §1.1 Customer Entity (CustomerProfile) | UUID v4, identity, residence, employment, `fcra_consent_log[]`, `pii_clearance_level` |
| `03_implementation_dummy_data_plan.md` | §1.2 Vehicle Entity (InventoryUnit) | `sb766_offering_price`, `add_ons[]` with `benefit_statement`, `compliance_check_passed` |
| `03_implementation_dummy_data_plan.md` | §1.3 Deal Structure Entity (DealJacket) | `financial_structure`, `tax_calculation`, `trade_in`, `lending_terms`, `audit_trail[]` |
| `03_implementation_dummy_data_plan.md` | §1.4 Regulatory Event Entity (ComplianceLog) | Reg B reason codes, `notice_details`, `credit_data_used` |
| `03_implementation_dummy_data_plan.md` | §0.3.1 California SB 766 & SB 478 | `sb766_offering_price` distinct from `price`; `add_ons` with benefit verification |
| `03_implementation_dummy_data_plan.md` | §3.1 Reference Data | Tax jurisdictions, lender programs, adverse action codes |

---

## Files to Create

| File | Purpose |
|------|---------|
| `data/migrations/001_add_customers_table.sql` | Create `customers` table with FCRA consent log support |
| `data/migrations/002_add_deals_table.sql` | Create `deals` table with full DealJacket schema |
| `data/migrations/003_extend_inventory.sql` | Add `sb766_offering_price`, `add_ons` JSON column to `inventory` |
| `data/migrations/004_extend_audit_logs.sql` | Add `payload_hash`, `actor`, `regulatory_flags` to `audit_logs` |
| `data/migrations/005_extend_lender_rules.sql` | Add `days_basis`, `dealer_reserve_cap`, `stips_required` |
| `data/reference/tax_rates.csv` | 100 tax jurisdictions (CA, AZ, NV, TX, FL focus) |
| `data/reference/adverse_action_codes.json` | 25 Reg B reason codes |
| `data/reference/lender_programs.json` | 50 lender programs (5 lenders × 5 tiers × 2 terms) |
| `backend/app/models/customer.py` | Pydantic model for CustomerProfile |
| `backend/app/models/deal.py` | Pydantic model for DealJacket |
| `backend/app/models/compliance_log.py` | Pydantic model for ComplianceLog |

---

## Files to Modify

| File | Changes |
|------|---------|
| `data/schema.sql` | Add new tables inline (for fresh installs) |
| `backend/app/models/schemas.py` | Add `OfferingPrice`, `AddOn`, `TradeIn`, `TaxCalculation` models |
| `backend/app/models/__init__.py` | Export new models |
| `scripts/seed_data.py` | Load reference data (tax rates, adverse codes, lender programs) |

---

## Schema Specifications

### customers table
```sql
CREATE TABLE customers (
    id TEXT PRIMARY KEY,  -- UUID v4
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system TEXT,
    pii_clearance_level TEXT CHECK(pii_clearance_level IN ('low', 'medium', 'high_sensitivity')),
    -- Identity (encrypted/tokenized)
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone_primary TEXT,
    date_of_birth DATE,
    ssn_masked TEXT,  -- ***-**-1234
    ssn_token TEXT,   -- vault reference
    -- Residence
    street TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    residence_type TEXT CHECK(residence_type IN ('own', 'rent', 'other')),
    -- Employment
    employer_name TEXT,
    monthly_gross_income REAL,
    -- FCRA Consent (JSON array)
    fcra_consent_log TEXT  -- JSON: [{consent_id, type, granted_at, ip_address, expires_at}]
);
```

### deals table
```sql
CREATE TABLE deals (
    id TEXT PRIMARY KEY,  -- deal_XXXXXX
    customer_id TEXT REFERENCES customers(id),
    vehicle_id INTEGER REFERENCES inventory(id),
    deal_status TEXT CHECK(deal_status IN ('working', 'desked', 'contracted', 'funded', 'unwound')),
    deal_type TEXT CHECK(deal_type IN ('retail_finance', 'lease', 'cash')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Financial Structure (JSON)
    selling_price REAL,
    rebates_total REAL DEFAULT 0,
    cash_down_payment REAL DEFAULT 0,
    trade_in TEXT,  -- JSON: {has_trade, allowance, payoff_amount, equity_amount, negative_equity_financed}
    tax_calculation TEXT,  -- JSON: {jurisdiction_code, tax_rate_combined, taxable_basis, total_sales_tax, rule_applied}
    fees TEXT,  -- JSON: {doc_fee, license_fee, registration_fee, total_fees}
    lending_terms TEXT,  -- JSON: {lender_id, program_tier, term_months, buy_rate, contract_apr, days_basis, amount_financed, monthly_payment, total_of_payments, finance_charge}
    -- Audit Trail (JSON array)
    audit_trail TEXT  -- JSON: [{timestamp, user_id, action, previous_value, new_value}]
);
```

### inventory extensions
```sql
ALTER TABLE inventory ADD COLUMN sb766_offering_price REAL;
ALTER TABLE inventory ADD COLUMN add_ons TEXT;  -- JSON: [{add_on_id, name, price, benefit_statement, compliance_check_passed}]
ALTER TABLE inventory ADD COLUMN store_id TEXT;
```

### audit_logs extensions
```sql
ALTER TABLE audit_logs ADD COLUMN transaction_id TEXT;  -- UUID
ALTER TABLE audit_logs ADD COLUMN actor TEXT;  -- user | agent:conversationalist | agent:fin_calc | agent:compliance
ALTER TABLE audit_logs ADD COLUMN event_type TEXT;  -- rate_inquiry | soft_pull_consent | adverse_action_generated | disclosure_presented
ALTER TABLE audit_logs ADD COLUMN payload_hash TEXT;  -- SHA-256 hex
ALTER TABLE audit_logs ADD COLUMN regulatory_flags TEXT;  -- JSON: {fcra_compliant, sb766_disclosure_verified, adverse_action_reason_code}
```

### lender_rules extensions
```sql
ALTER TABLE lender_rules ADD COLUMN days_basis TEXT DEFAULT '30/360';  -- 30/360 | actual/365 | 365/360
ALTER TABLE lender_rules ADD COLUMN dealer_reserve_cap REAL DEFAULT 2.5;
ALTER TABLE lender_rules ADD COLUMN stips_required TEXT;  -- JSON array: ["poi", "por", "references"]
```

---

## Reference Data Specifications

### tax_rates.csv (100 rows)
```csv
zip_code,state,city,county,county_rate,city_rate,state_rate,combined_rate,special_district_rate,tax_basis_rule,trade_in_credit
92101,CA,San Diego,San Diego,0.0025,0.0000,0.0725,0.0775,0.0025,DESTINATION_BASED,FALSE
85001,AZ,Phoenix,Maricopa,0.007,0.023,0.056,0.086,0.000,DESTINATION_BASED,TRUE
```

### adverse_action_codes.json (25 codes)
```json
[
  {"code": "A01", "text": "Income insufficient for amount of credit requested"},
  {"code": "A02", "text": "Excessive obligations in relation to income"},
  {"code": "A06", "text": "Unable to verify employment"},
  {"code": "A12", "text": "Length of employment"},
  {"code": "B01", "text": "Value or type of collateral not sufficient"},
  {"code": "C01", "text": "Too few bank references"},
  {"code": "D01", "text": "Credit application incomplete"}
]
```

### lender_programs.json (50 programs)
Schema per `02_strategic_blueprint.md` §3.2.1:
```json
{
  "lender_id": "ALLY",
  "effective_date": "2026-01-01",
  "programs": [
    {
      "tier": "S",
      "min_fico": 750,
      "max_ltv": 1.20,
      "rates": [
        {"term": 60, "apr": 4.99, "dealer_reserve_cap": 2.0},
        {"term": 72, "apr": 5.49, "dealer_reserve_cap": 2.0}
      ],
      "stips_required": []
    }
  ]
}
```

---

## Acceptance Tests

### Test File: `backend/tests/test_data_foundation.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T01-01 | `test_customers_table_exists` | `SELECT * FROM customers` does not error |
| T01-02 | `test_customer_uuid_format` | Customer ID matches UUID v4 regex |
| T01-03 | `test_customer_fcra_consent_json` | `fcra_consent_log` parses as valid JSON array |
| T01-04 | `test_deals_table_exists` | `SELECT * FROM deals` does not error |
| T01-05 | `test_deal_status_constraint` | INSERT with `deal_status='invalid'` raises error |
| T01-06 | `test_deal_foreign_keys` | Deal with invalid `customer_id` raises FK error |
| T01-07 | `test_inventory_sb766_price` | `sb766_offering_price` column accessible |
| T01-08 | `test_inventory_addons_json` | `add_ons` parses as valid JSON array |
| T01-09 | `test_audit_logs_payload_hash` | `payload_hash` accepts 64-char hex string |
| T01-10 | `test_lender_rules_days_basis` | `days_basis` defaults to '30/360' |
| T01-11 | `test_tax_rates_loaded` | `tax_rates` table has >= 100 rows |
| T01-12 | `test_adverse_codes_loaded` | `adverse_action_codes` table has >= 25 rows |
| T01-13 | `test_lender_programs_loaded` | `lender_rules` table has >= 50 rows |
| T01-14 | `test_ca_tax_no_tradein_credit` | CA zip returns `trade_in_credit=FALSE` |
| T01-15 | `test_az_tax_tradein_credit` | AZ zip returns `trade_in_credit=TRUE` |

### Test File: `backend/tests/test_pydantic_models.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T01-16 | `test_customer_profile_validation` | CustomerProfile rejects invalid email format |
| T01-17 | `test_deal_jacket_validation` | DealJacket rejects negative `selling_price` |
| T01-18 | `test_compliance_log_reason_codes` | ComplianceLog validates reason code format |
| T01-19 | `test_addon_benefit_statement` | AddOn with `benefit_statement=None` and `compliance_check_passed=True` raises error |

---

## Definition of Done

- [ ] All 5 migration files created and run successfully
- [ ] All 3 reference data files created with specified volumes
- [ ] All Pydantic models created and exported
- [ ] `seed_data.py` loads reference data on fresh install
- [ ] All 19 acceptance tests pass
- [ ] No regressions in existing tests (`pytest tests/`)
