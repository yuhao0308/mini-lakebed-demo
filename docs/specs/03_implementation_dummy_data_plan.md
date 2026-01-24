# Implementation-Grade Data + Dummy Data Plan: The Mini-Lakebed AI Ecosystem

---

## 0. System Boundaries and Architectural Scope

### 0.1 Executive Summary of Technical Scope

This document serves as the definitive implementation plan for the data architecture underlying the 'Mini-Lakebed AI Ecosystem' for automotive retail. The objective is to engineer a compliant, deterministic, and agentic data environment that supports a fully functional dealership demo. This system must handle the complexity of automotive transactions—ranging from penny-perfect financial calculations to strict regulatory adherence (SB 766, Regulation B, FCRA)—while maintaining a governance-first posture via OpenFGA and immutable audit logs.

The scope encompasses the full lifecycle of data: ingestion from lead sources (ADF XML), internal processing of credit applications (JSON), deterministic calculation of deal structures (Desking), and the finalization of compliant contracts. The architecture is designed to be "implementation-ready," providing explicit schemas, synthetic data strategies, and governance models required to build the system immediately.

This architecture is not merely a data store; it is a **"Mini-Lakebed"** designed to support Agentic AI. Unlike traditional architectures where applications hold logic and databases hold state, this ecosystem treats the **Data Layer as the primary enforcement point** for business logic, regulatory compliance, and state transitions. The AI agents act as transient compute nodes that request permission to act upon this governed layer, ensuring that even a hallucinating agent cannot violate federal law or business rules.

### 0.2 System Components and Boundaries

The ecosystem is bounded by four primary interfaces, each serving as a distinct domain with specific protocols for data ingress, egress, and transformation. These boundaries are enforced via API contracts and strict schema validation to prevent "data swamp" conditions in the lakebed.

#### 0.2.1 Ingestion Layer (The "Lot")

This boundary represents the chaotic, external-facing edge of the system. It is responsible for accepting "dirty," unstructured, or semi-structured data from external parties. In the automotive context, this includes Original Equipment Manufacturer (OEM) inventory feeds, Auto-Lead Data Format (ADF) XML leads from third-party aggregators (like Autotrader or Cars.com), and JSON payloads from credit bureaus.

- **Function:** Ingress, buffering, and normalization.
- **Protocol:** Accepts SMTP (for email-based ADF leads) and HTTPS POST (for API-based inventory updates).
- **Data State:** Data here is considered "untrusted" until it passes the schema validation gates.
- **Security:** This layer sits in the DMZ (Demilitarized Zone), scrubbing inputs for injection attacks before passing them to the internal message bus.

#### 0.2.2 Processing Layer (The "Desk")

The "Desk" is the core transactional engine where deterministic math applies. This boundary enforces business logic and state management. It is here that the abstract concept of a "Lead" is transformed into the concrete financial structure of a "Deal."

- **Function:** Calculation, Desking, structuring, and state transitions.
- **Key Logic:** This layer houses the "Penny-Perfect" calculation engine. It enforces California-specific tax rules where trade-in equity does not reduce the taxable basis[^1], and strictly defines "Offering Price" per SB 766.[^3]
- **Data State:** Data here is "hot" and transactional. It is highly structured and relational.

#### 0.2.3 Governance Layer (The "Vault")

A horizontal layer that permeates the entire architecture, the "Vault" is responsible for authorization, identity, and audit. It enforces access control via OpenFGA (Fine-Grained Authorization)[^4], handles PII (Personally Identifiable Information) scrubbing, and maintains the immutable ledger of adverse actions and consent events.

- **Function:** Authorization, Audit, PII Redaction.
- **Key Logic:** It enforces the "Need to Know" principle. A Sales Representative agent may read a customer's name but must be blocked from reading the raw Credit Score unless specific "permissible purpose" conditions are met under the FCRA.
- **Data State:** Immutable. Once a compliance log is written, it cannot be altered, only appended to.

#### 0.2.4 Agentic Interface (The "Agent")

The AI-driven surface that interacts with the data. This layer consumes the canonical data model to execute workflows (e.g., "Draft a decline letter for applicant X") but does not store state independent of the Processing Layer.

- **Function:** Inference, Natural Language Processing (NLP), and Action execution.
- **Key Logic:** The agents are stateless. They must retrieve context from the Processing Layer and permissions from the Governance Layer for every action.
- **Constraint:** An agent cannot "invent" a price. It must query the "Offering Price" from the governed database to ensure compliance with SB 478/SB 766, preventing the hallucination of discounts that don't exist.[^5]

### 0.3 Regulatory Constraints & Compliance Boundaries

The data plan is strictly bounded by the following regulatory frameworks, which dictate schema requirements. These are not optional features but hard constraints on the data model.

#### 0.3.1 California SB 766 & SB 478 (CARS Act)

These regulations fundamentally change how pricing data must be modeled. The system must distinctly store an "Offering Price" separate from the "Total Price."

- **Constraint:** The "Offering Price" is the full cash price excluding only required government charges. The system must prevent "drip pricing," where fees are added later in the funnel.
- **Schema Impact:** The `Inventory` entity cannot just have a `price` field. It must have `msrp`, `invoice`, and a legally binding `sb766_offering_price`.[^3]
- **Valueless Add-ons:** The data model must link every added product (e.g., Nitrogen, Theft Patrol) to a "benefit" verification field. If an add-on is flagged as having no benefit to the specific vehicle (e.g., oil changes for an EV), the schema validation must reject the deal structure.[^7]

#### 0.3.2 Regulation B (Equal Credit Opportunity Act)

Reg B mandates precise communication regarding credit denials (Adverse Action).

- **Constraint:** When a deal is rejected based on credit, the system must capture the specific principal reasons (up to four) derived from the credit scoring model.
- **Schema Impact:** The `ComplianceLog` entity must support an array of reason codes (e.g., "A01 - Income insufficient for amount of credit requested") rather than free-text notes.[^9]

#### 0.3.3 FCRA (Fair Credit Reporting Act)

This governs the access to consumer credit reports.

- **Constraint:** A "Soft Pull" cannot occur without "written instruction" from the consumer.
- **Schema Impact:** The `Customer` entity requires a nested `ConsentLog` capturing the exact timestamp, IP address, user agent, and the specific version of the legal text agreed to by the consumer.[^11]

#### 0.3.4 Truth in Lending Act (Regulation Z)

This dictates the mathematical precision of financial disclosures.

- **Constraint:** The Annual Percentage Rate (APR) and Finance Charge must be calculated within a specific tolerance ($0.125%).
- **Schema Impact:** Financial fields must use `Decimal` types with high precision (minimum 4 decimal places for rates, 2 for currency) to prevent floating-point drift. The system must also support specific interest accrual methods (e.g., 365/360 vs. Simple Interest) as defined in the lender's program.[^13]

---

## 1. Canonical Domain Data Model

The Canonical Domain Data Model (CDDM) serves as the "Lingua Franca" of the Mini-Lakebed. All incoming data (regardless of source format—XML, JSON, CSV) must be transformed into these strict schemas before entering the Processing Layer. This ensures that the AI agents always interact with clean, typed, and governed data.

### 1.1 Customer Entity (CustomerProfile)

This entity represents the potential buyer. It acts as the anchor for identity, contact information, and credit authority.

**Design Rationale:**

- **ID Strategy:** UUID v4 is mandatory. Using sequential integers (e.g., Customer 1001, 1002) allows for enumeration attacks where a malicious actor could guess IDs to scrape PII.
- **Consent Architecture:** `fcra_consent_log` is modeled as a nested array of objects, not a simple boolean. Consent is temporal; a customer may consent today, the consent expires in 30 days, and they must re-consent. The data model must preserve the entire history for audit purposes.[^11]
- **AI Safety:** The `pii_clearance_level` field dictates visibility. An AI agent with "Low" clearance will receive a version of this object with the SSN and DOB masked, allowing it to perform tasks (e.g., "Draft an email") without exposing sensitive data.

```json
{
  "customer_id": "c7b3d8e0-5e0a-4b9f-8f2a-3d9c7e1f6a2b",
  "meta": {
    "created_at": "2026-01-22T14:30:00Z",
    "source_system": "lead_aggregator_autotrader",
    "pii_clearance_level": "high_sensitivity"
  },
  "identity": {
    "first_name": "James",
    "last_name": "Morris",
    "middle_initial": "T",
    "email": "j.morris@example.com",
    "phone_primary": "+1-555-010-9988",
    "phone_type": "mobile",
    "date_of_birth": "1985-04-12",
    "ssn_masked": "***-**-6789",
    "ssn_token": "vault_token_88229911"
  },
  "residence": {
    "street": "123 El Camino Real",
    "unit": "Apt 4B",
    "city": "San Diego",
    "state": "CA",
    "zip": "92101",
    "county": "San Diego",
    "years_at_residence": 3,
    "months_at_residence": 2,
    "residence_type": "rent"
  },
  "employment": {
    "employer_name": "TechFlow Systems",
    "job_title": "Systems Analyst",
    "years_employed": 4,
    "monthly_gross_income": 8500.00,
    "income_verification_status": "verified_paystub",
    "other_income": 0.00
  },
  "fcra_consent_log": [
    {
      "consent_id": "consent_001",
      "consent_type": "soft_pull",
      "granted_at": "2026-01-22T14:35:00Z",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "legal_text_version": "v2026.1",
      "expires_at": "2026-02-21T14:35:00Z"
    }
  ]
}
```

### 1.2 Vehicle Entity (InventoryUnit)

Represents the physical asset. In the automotive domain, the vehicle is not just a product; it is a collection of compliance attributes.

**Design Rationale:**

- **VIN Precision:** The VIN serves as the natural key for uniqueness checks, but the system relies on `inventory_id` for internal relationships to allow for situations where a VIN might be entered erroneously and later corrected.
- **Pricing Compliance:** Per SB 766, the "Offering Price" is the legally binding advertisement. The system must store this explicitly. Dynamic calculation of price at runtime is dangerous because if an algorithm changes, the "historical" price offered to a customer might change, violating the CARS Act.[^3]
- **Valueless Add-ons:** The `add_ons` array includes a `benefit_statement`. The pipeline will validate this. For example, if `fuel_type` is "Electric" and an add-on is "Oil Change Plan," the `compliance_check_passed` field will default to `false`, preventing the sale.[^8]

```json
{
  "inventory_id": "inv_2026_001",
  "vin": "1G1YC2D4X85123456",
  "stock_number": "P10293",
  "status": "in_stock",
  "descriptor": {
    "year": 2024,
    "make": "Chevrolet",
    "model": "Silverado 1500",
    "trim": "LT Trail Boss",
    "body_type": "Crew Cab",
    "fuel_type": "Gasoline",
    "odometer_reading": 15,
    "odometer_unit": "miles",
    "color_exterior": "Summit White",
    "color_interior": "Jet Black"
  },
  "pricing": {
    "msrp": 58900.00,
    "invoice_price": 56200.00,
    "sb766_offering_price": 58900.00,
    "currency": "USD",
    "price_effective_date": "2026-01-01"
  },
  "add_ons": [
    {
      "add_on_id": "ao_001",
      "name": "Nitrogen Tire Fill",
      "price": 199.00,
      "benefit_statement": "Maintains tire pressure longer in extreme temperatures.",
      "compliance_check_passed": true
    },
    {
      "add_on_id": "ao_002",
      "name": "Theft Deterrent Etching",
      "price": 299.00,
      "benefit_statement": null,
      "compliance_check_passed": false
    }
  ],
  "location": {
    "store_id": "store_sd_01",
    "lot_location": "Row 4, Slot 12"
  }
}
```

### 1.3 Deal Structure Entity (DealJacket)

The `DealJacket` is the aggregation of Customer, Vehicle, and Financial logic. This is the most complex schema as it handles the "penny-perfect" math and structural compliance.

**Design Rationale:**

- **Tax Basis Logic:** The schema explicitly separates `taxable_basis_amount`. In California, this equals `selling_price + taxable_fees`. In states like Arizona, it is `selling_price - trade_in_value`. The schema must store the calculated basis to ensure that audit logs can reconstruct exactly how the tax was derived.[^1]
- **Regulation Z Fields:** `apr`, `finance_charge`, and `total_of_payments` are distinct fields. They are not merely derived on the fly for display; they are persisted to ensure that the contract generated matches the database record exactly.
- **Trade-In Equity:** The `trade_in` object captures `negative_equity_financed`. If a customer owes $18k on a car worth $15k, the $3k deficit is added to the new loan. This affects the Loan-to-Value (LTV) ratio, which determines lender eligibility.

```json
{
  "deal_id": "deal_554433",
  "customer_ref": "c7b3d8e0-5e0a-4b9f-8f2a-3d9c7e1f6a2b",
  "vehicle_ref": "inv_2026_001",
  "deal_status": "working",
  "financial_structure": {
    "deal_type": "retail_finance",
    "selling_price": 58900.00,
    "rebates_total": 1500.00,
    "cash_down_payment": 5000.00,
    "trade_in": {
      "has_trade": true,
      "allowance": 25000.00,
      "payoff_amount": 18000.00,
      "equity_amount": 7000.00,
      "negative_equity_financed": 0.00,
      "vin": "VIN_TRADE_OLD_001"
    },
    "tax_calculation": {
      "jurisdiction_code": "CA_SAN_DIEGO_92101",
      "tax_rate_combined": 0.0775,
      "taxable_basis": 58900.00,
      "total_sales_tax": 4564.75,
      "rule_applied": "CA_FULL_PRICE_BASIS"
    },
    "fees": {
      "doc_fee": 85.00,
      "license_fee": 420.00,
      "registration_fee": 150.00,
      "electronic_filing_fee": 30.00,
      "total_fees": 685.00
    },
    "lending_terms": {
      "lender_id": "lender_chase_01",
      "program_tier": "Tier 1",
      "term_months": 72,
      "buy_rate": 0.0525,
      "contract_apr": 0.0625,
      "dealer_reserve": 0.0100,
      "days_basis": "365/360",
      "amount_financed": 52649.75,
      "monthly_payment": 845.23,
      "total_of_payments": 60856.56,
      "finance_charge": 8206.81
    }
  },
  "audit_trail": [
    {
      "timestamp": "2026-01-22T15:00:00Z",
      "user_id": "user_sales_001",
      "action": "deal_created",
      "previous_value": null,
      "new_value": "initial_structure"
    }
  ]
}
```

**Deal Status Values:**
- `working` - Deal in progress
- `desked` - Pricing finalized
- `contracted` - Customer signed
- `funded` - Lender funded
- `unwound` - Deal cancelled/reversed

**Deal Type Values:**
- `retail_finance` - Traditional financing
- `lease` - Lease agreement
- `cash` - Cash purchase

### 1.4 Regulatory Event Entity (ComplianceLog)

This entity tracks Adverse Actions and other mandated disclosures. It is the "black box" recorder for the dealership's compliance posture.

**Design Rationale:**

- **Reason Codes:** The schema enforces the use of Regulation B specific codes. An AI agent cannot simply say "Bad Credit"; it must map the rejection to a standard code like "A01" to generate the legal letter.[^9]
- **Transmission Evidence:** It is not enough to generate the notice; the system must track how and when it was sent to the consumer to prove compliance during an audit.

```json
{
  "log_id": "log_888221",
  "related_deal_id": "deal_554433",
  "customer_ref": "c7b3d8e0-5e0a-4b9f-8f2a-3d9c7e1f6a2b",
  "event_type": "adverse_action_notice",
  "trigger_date": "2026-01-22",
  "credit_data_used": {
    "bureau_source": "Experian",
    "score_date": "2026-01-22",
    "credit_score": 620
  },
  "denial_reasons": [
    {
      "code": "A01",
      "text": "Income insufficient for amount of credit requested"
    },
    {
      "code": "A12",
      "text": "Length of employment"
    }
  ],
  "notice_details": {
    "notice_generated": true,
    "notice_sent_method": "email",
    "notice_sent_timestamp": "2026-01-22T15:00:00Z",
    "email_message_id": "msg_aws_ses_998877"
  }
}
```

---

## 2. End-to-End Pipeline Architecture

The pipeline is designed to be **event-driven** and **idempotent**. A reprocessing of the same Lead ID should result in the same Deal structure unless the underlying rules or inventory status have changed.

### 2.1 Stage 1: Ingestion & Normalization (The "Air Lock")

**Mechanism:**

- **Transport:** The system listens for incoming ADF 1.0 XML payloads via a secure webhook endpoint.
- **Parsing:** An ingestion worker utilizes a SAX parser to traverse the XML structure. It specifically targets the `<prospect>` nodes.
- **ADF Handling:** The parser must handle the `<adf num_leads="N">` attribute. If a single file contains multiple leads, the worker spawns N distinct processing threads, one for each lead.[^16]

**Mapping:** The worker maps the XML tags to the `CustomerProfile` schema.

| ADF XML Path | Target Field |
|--------------|--------------|
| `<customer><contact><name part="first">` | `identity.first_name` |
| `<vehicle interest="buy">` | Signals a `retail_finance` intent |
| `<vehicle interest="lease">` | Signals a `lease` intent |
| `<id sequence="1">` | External ID logged to prevent duplicate processing[^17] |

**Validation:** The system checks for the presence of the `<vehicle>` block. If missing, the lead is flagged as "General Inquiry" rather than "Vehicle Specific," triggering a different routing workflow.

### 2.2 Stage 2: Enrichment & Compliance Check

**Mechanism:**

1. **Soft Pull Trigger:** The pipeline inspects the `CustomerProfile` for the existence of a valid `fcra_consent_log` entry.
   - **If Present:** The system calls the 700Credit/DealerTrack API (mocked for the demo) to retrieve the FICO score and Auto Trade Lines.
   - **If Absent:** The system triggers an "Agent Action" to email the customer a consent link. The pipeline pauses here for this specific deal path.

2. **OFAC Check:** The customer's name is screened against the Office of Foreign Assets Control (OFAC) Specially Designated Nationals (SDN) list. A hit freezes the pipeline immediately.

3. **Inventory Validation:** The requested vehicle (by Stock Number or VIN) is checked against the `InventoryUnit` database.

4. **Valueless Product Check:** The pipeline iterates through the `add_ons` array for the vehicle. If any add-on has `compliance_check_passed: false` (e.g., Nitrogen on a vehicle where the dealer failed to document the purity level benefit), the deal is flagged for Manager Review before pricing can be calculated.[^7]

### 2.3 Stage 3: The Deterministic Calculation Engine (The "Brain")

This is the core component that guarantees "penny-perfect" accuracy. It operates using the **Strategy Pattern** to select the correct algorithms based on jurisdiction.

**Step-by-Step Logic:**

#### Step 1: Tax Determination

The engine pulls the `zip_code` from the `CustomerProfile`. It queries the `TaxRateTable` (Reference Dataset).

**Logic Branch:**

```
If State == 'CA' (California):
    Tax_Basis = Selling_Price + Taxable_Fees
    // The Trade-In value is ignored for tax purposes [^1]

If State == 'AZ' (Arizona):
    Tax_Basis = (Selling_Price + Taxable_Fees) - Trade_Allowance
    // The Trade-In reduces the tax burden [^1]
```

#### Step 2: Fee Injection

The engine injects mandatory state fees based on the dealership's location.

**Example:**
- California Doc Fee is capped (e.g., $85)
- Florida Doc Fee is uncapped but must be consistent

The engine applies the fee defined in the `StoreProfile` configuration.

#### Step 3: Lender Matching

The engine queries the `LenderRateSheet` dataset.

- **Input:** Customer FICO (e.g., 740), Vehicle Age (e.g., New), LTV (e.g., 90%)
- **Filtering:** It filters out lenders where the LTV exceeds the program max (e.g., 120%) or the credit score is below the minimum (e.g., 600)
- **Selection:** It selects the "Best Buy Rate" (lowest interest rate) available for the customer's tier

#### Step 4: Amortization

The engine calculates the `Monthly_Payment` using the specific Day Count Convention (e.g., Actual/365 or 30/360) mandated by the selected lender.[^14] This ensures that the payment generated matches the lender's contract exactly.

### 2.4 Stage 4: Governance & Persistence

**Mechanism:**

1. **Persistence:** The finalized `DealJacket` is written to the Operational Database (Postgres with JSONB support) for the Agent to access. A copy is written to the Data Lake (Parquet format) for long-term analytics.

2. **Authorization:** Simultaneously, the pipeline writes the OpenFGA relationship tuples to lock down access.

```
write(user="user:sales_rep_1", relation="viewer", object="deal:deal_554433")
write(user="user:sales_manager", relation="editor", object="deal:deal_554433")
write(user="user:compliance_officer", relation="auditor", object="deal:deal_554433")
```

3. **Audit Logging:** An entry is made in the `ComplianceLog` noting the creation of the deal, the specific pricing used (referencing the `sb766_offering_price` ID), and the user/process responsible.

---

## 3. Dummy Data Specification

To effectively stress-test this architecture and demonstrate the AI's capabilities, we require a comprehensive set of dummy data. Random generation is insufficient; the data must be **semantically valid** to pass the rigorous compliance checks built into the pipeline.

### 3.1 Dataset A: Reference Data (The "Static" Layer)

This data represents the immutable laws of the automotive universe: taxes, lender rules, and reason codes.

#### 3.1.1 Tax Jurisdiction Table (`tax_rates.csv`)

Based on[^18], we need a CSV covering varied tax scenarios to test the logic branching.

- **Volume:** 50 rows (Focus on CA, AZ, NV, TX, FL)
- **Schema:** `ZipCode`, `State`, `City`, `CountyRate`, `CityRate`, `StateRate`, `CombinedRate`, `SpecialDistrictRate`, `TaxBasisRule`

**Columns Logic:**

| Column | Description |
|--------|-------------|
| `TaxBasisRule` | Enum: `DESTINATION_BASED`, `ORIGIN_BASED` |
| `TradeInCredit` | Boolean. `FALSE` for CA, `TRUE` for AZ |

**Example Record:**
```
92101, CA, San Diego, 0.0025, 0.0000, 0.0725, 0.0775, 0.0025, DESTINATION_BASED, FALSE
```

#### 3.1.2 Lender Rate Sheets (`lender_programs.json`)

This dataset drives the "Desking" logic. It must define the constraints for loan approval.

- **Volume:** 5 Lenders (2 Captive like "Ford Motor Credit", 2 Major Banks like "Chase", 1 Credit Union)
- **Schema:** Tiers, Term Limits, Max LTV, Fee Caps, Day Count Method

**Example Record:**

```json
{
  "lender_name": "AmeriCredit Dummy Bank",
  "program_id": "ACB_PRIME_2026",
  "calc_method": "365/360",
  "tiers": [
    {
      "tier_name": "Super Prime",
      "min_fico": 750,
      "max_ltv": 1.20,
      "rates": [
        { "term": 60, "apr": 0.0499 },
        { "term": 72, "apr": 0.0549 }
      ]
    },
    {
      "tier_name": "Prime",
      "min_fico": 700,
      "max_ltv": 1.10,
      "rates": [
        { "term": 60, "apr": 0.0649 },
        { "term": 72, "apr": 0.0699 }
      ]
    }
  ]
}
```

#### 3.1.3 Regulation B Reason Codes (`adverse_action_codes.json`)

Derived strictly from Regulation B appendixes.[^9]

- **Volume:** Full set of standard codes (approx. 25)

**Example Records:**

```json
{ "code": "A01", "text": "Income insufficient for amount of credit requested" }
{ "code": "A06", "text": "Unable to verify employment" }
{ "code": "A12", "text": "Length of employment" }
{ "code": "B01", "text": "Value or type of collateral not sufficient" }
```

### 3.2 Dataset B: Transactional Data (The "Dynamic" Layer)

#### 3.2.1 Lead/Customer Corpus (`leads.adf.xml`)

**Volume Recommendation:** 5,000 unique leads

**Distribution Strategy:**

| Segment | Percentage | Purpose |
|---------|------------|---------|
| Prime (Score > 700) | 60% | "Happy Path" pipeline testing |
| Subprime (Score < 620) | 30% | Adverse Action logic testing |
| Edge Case | 10% | Negative Equity, Out of State, Missing Data |

**Synthetic Logic:** Use a library like `Faker` but heavily modified.

- **Names:** Exclude protected names or offensive terms
- **Addresses:** Must map strictly to the `tax_rates.csv` file. A random zip code like `99999` will cause the Tax Engine to fail. The generator must pick zip codes from the reference file.

#### 3.2.2 Inventory Corpus (`inventory.json`)

**Volume:** 1,000 vehicles

**Schema Enforcement:**

- **VINs:** Use a VIN generator that calculates valid checksums. Invalid VINs should be generated only for specific "Error Handling" test cases.
- **Pricing:** Ensure `invoice < msrp`
- **Age Distribution:**
  - 50% New (Current Year)
  - 40% Used (< 5 years old)
  - 10% Aged/Wholesale

**SB 766 Compliance Data:** For 10% of Used cars, generate "Add-ons" (e.g., "Theft Etch") that are flagged as `benefit_statement: null`. This provides the test data necessary to verify that the pipeline correctly blocks non-compliant sales.[^7]

#### 3.2.3 Credit Bureau Responses (`bureau_mock.json`)

**Purpose:** To simulate the JSON response from 700Credit.

**Schema:**

```json
{
  "applicant_ref": "c7b3d8e0-...",
  "fico_score": 645,
  "score_factors": ["A01", "A12"],
  "auto_trade_lines": {
    "open_auto_loans": 1,
    "current_balance": 12500.00,
    "monthly_payment": 350.00
  }
}
```

**Insight:** The `current_balance` here feeds into the Trade-In logic. If the customer trades this car, and the allowance is $10k, the system calculates $2,500 negative equity.

---

## 4. Deterministic Math Specifications

The system cannot rely on standard floating-point math (e.g., `float` in Python or `double` in C#). Financial calculations require **Arbitrary-Precision Arithmetic** (e.g., `decimal` in Python, `BigDecimal` in Java) to avoid rounding errors that would cause contract rejection by banks.

### 4.1 Interest Calculation Algorithms

Automotive loans use specific day-count conventions that differ from standard mortgages. The plan must support three variants to be truly "implementation-grade".[^13]

#### Method A: 30/360 (Standard Consumer)

- **Concept:** Assumes every month has 30 days and a year has 360 days. This simplifies the math for consumers and provides a consistent monthly payment.
- **Formula:** $$I = P \times R \times \frac{30}{360}$$
- **Implementation:** `interest_payment = principal * (annual_rate / 12)`
- **Use Case:** Most standard retail installment contracts (RISC)

#### Method B: Actual/365 (Simple Interest)

- **Concept:** Interest accrues daily based on the actual number of days in the year (365).
- **Formula:** $$I = P \times R \times \frac{d}{365}$$ where $d$ is actual days elapsed since the last payment
- **Implementation:** `daily_rate = annual_rate / 365; interest = principal * daily_rate * days_in_period`
- **Implication:** If a customer pays 5 days late, they pay 5 days more interest. The system must account for this in the "Payoff Quote" calculation.

#### Method C: 365/360 (The "Bank" Method)

- **Concept:** This method is often used in commercial lending. It calculates the daily rate based on a 360-day year (making the rate higher) but charges for the actual 365 days.
- **Formula:** $$I = P \times R \times \frac{d}{360}$$
- **Effective Rate:** This effectively increases the stated interest rate by a factor of $365/360$ (approx. 1.39% higher finance charge)[^13]
- **Compliance Warning:** Using this on a consumer loan without explicit disclosure is a Truth in Lending violation. The system must default to 30/360 for consumer deals unless the `deal_type` is "commercial_fleet."

### 4.2 Tax Calculation Logic (California Trade-In Rule)

The calculation engine must implement a conditional logic branch for the "Taxable Basis." This is where many generic e-commerce engines fail in automotive.

**Formula Logic:**

$$
\text{Taxable Basis} = \begin{cases}
\text{Price}_{\text{vehicle}} + \text{Fees}_{\text{taxable}} & \text{if State} = \text{CA, MI, VA} \\
(\text{Price}_{\text{vehicle}} + \text{Fees}_{\text{taxable}}) - \text{Trade}_{\text{allowance}} & \text{if State} = \text{AZ, NV, TX}
\end{cases}
$$

**California Specifics:** Research citation[^1] confirms CA taxes the full price of the new vehicle. The trade-in value is applied as a credit *after* the tax calculation.

**Example:** Buying a $50k car, trading a $40k car.

| State | Calculation | Tax Amount |
|-------|-------------|------------|
| CA (8%) | $50,000 × 0.08 | $4,000 |
| AZ (8%) | ($50,000 - $40,000) × 0.08 | $800 |

**Impact:** The difference is **$3,200**. The demo system must show this difference explicitly when the "State" dropdown is toggled.

### 4.3 Regulation B: Adverse Action Logic

The math isn't just financial; it's logical. The system must determine *why* a deal failed.

- **Input:** Credit Score (645), Lender Minimum (680)
- **Logic:** `If Score < Min_Score THEN Trigger_Adverse_Action`
- **Output:** The system cannot simply say "Score too low." It must query the `bureau_mock` to retrieve the `score_factors`.
- **Mapping:** Factor "A01" → "Income insufficient."
- **Action:** Populate the `ComplianceLog` with these codes and generate the text for the letter.[^10]

---

## 5. Governance Controls: The OpenFGA Model

We will implement a **Relationship-Based Access Control (ReBAC)** model using OpenFGA. This is superior to standard Role-Based Access Control (RBAC) because automotive permissions are highly contextual (e.g., "I can edit this deal because I am the Finance Manager of the store where the deal originated," not just "I am a Finance Manager").

### 5.1 The Authorization Model (DSL)

Based on[^4], the following schema defines our governance. It introduces the concept of "Auditor" and "Restricted Viewer" to handle PII.

```dsl
model
  schema 1.1

type user

type dealership
  relations
    define member: [user]
    define general_manager: [user]
    define finance_manager: [user]
    define sales_manager: [user]

type deal
  relations
    define owner: [user]
    define dealership: [dealership]
    # A viewer can see the deal structure but not PII
    define viewer: [user, dealership#member] or editor
    # An editor can change numbers
    define editor: [user] or owner or dealership#finance_manager or dealership#sales_manager
    # An auditor can see the history but change nothing
    define auditor: [user] or dealership#general_manager

type compliance_log
  relations
    define viewer: [user] or deal#auditor
    # Only specific compliance officers can see the raw credit denial reasons
    define sensitive_viewer: [user]
```

### 5.2 Policy Enforcement Points (PEP)

#### 5.2.1 Deal Modification Lock

**Rule:** Only the `owner` (Salesperson) or `finance_manager` can mutate the `financial_structure` of a deal.

**Implementation:** Before any `UPDATE` SQL query is executed on the `DealJacket` table, the API Middleware calls `OpenFGA.Check(user=CurrentUser, relation='editor', object=CurrentDeal)`. If the result is `False`, the API returns `HTTP 403 Forbidden`.

#### 5.2.2 PII Access & "Need to Know"

**Rule:** The `customer_profile` object is protected. A generic `dealership#member` (e.g., a porter or receptionist) can view the Deal Structure (to see what car is being sold) but cannot view the Credit Report (Adverse Action details) unless they are the `finance_manager` or the specific `owner`.

**Implementation:** The UI renders the "Credit" tab only if `OpenFGA.Check(user=CurrentUser, relation='sensitive_viewer', object=ComplianceLog)` returns `True`.

#### 5.2.3 Audit Logs & Immutability

**Rule:** The `compliance_log` is append-only. Even a `general_manager` is a `viewer`, not an `editor`, ensuring immutability of the audit trail.

**Implementation:** The database user used by the API for the `ComplianceLog` table has `INSERT` and `SELECT` permissions only. `UPDATE` and `DELETE` are revoked at the database level.

### 5.3 PII Scrubbing & Data Masking for AI

**Strategy:** Data at rest is encrypted. Data in transit to the "Agent" (AI) is masked.

**Implementation:** Before passing the `CustomerProfile` to an LLM context window:

| Original Field | Masked Value |
|----------------|--------------|
| `ssn` | `***-**-6789` |
| `dob` | `YYYY-MM-01` (Age preservation for contract eligibility, day redaction for privacy) |
| `email` | `j****@mail.com` |

**Justification:** This allows the AI to perform logic ("Is the applicant over 18?") without exposing sensitive PII to the model provider, satisfying privacy-by-design principles.

---

## 6. Completeness Checklist for the Demo

To ensure the "implementation-grade" status, the following checklist must be verified against the generated Dummy Data and Pipeline logic. This serves as the User Acceptance Testing (UAT) plan.

### 6.1 Financial Completeness

- [ ] **Penny-Perfect Verification:** Does a $35,000 loan at 5% for 60 months result in exactly $660.49/mo using the 30/360 method?
- [ ] **Negative Equity Handling:** Does the system correctly add negative equity (Trade Payoff - Trade Allowance) to the new loan balance before calculating LTV?
- [ ] **Usury Cap Check:** Does the system throw a validation error if the computed APR exceeds the state usury limit (e.g., 25%) defined in the Reference Data?
- [ ] **Payment Packing Prevention:** Does the sum of `Monthly_Payment * Term` equal `Total_of_Payments` exactly? (Any deviation suggests hidden fees)

### 6.2 Regulatory Completeness (SB 766 / CARS / FCRA)

- [ ] **Offering Price Integrity:** Is the `sb766_offering_price` stored statically? Does the final contract price match `Offering_Price + Gov_Fees + Consumer_Selected_Addons` exactly?[^3]
- [ ] **Benefit Statement Validation:** Is there a hard block preventing "Nitrogen Fill" add-ons on a deal unless the `benefit_statement` field is populated and `compliance_check_passed` is `true`?[^8]
- [ ] **Consent Logging:** Does every Soft Pull request have a linked `fcra_consent_log` entry with a valid Timestamp and IP Address?[^12]
- [ ] **Cancellation Option Generation:** For used cars sold for less than $40,000, does the system automatically generate the data for the "2-Day/250-Mile Cancellation Option Agreement"?[^5]

### 6.3 Governance Completeness

- [ ] **Cross-Store Isolation:** Can a sales rep from Store A view a deal from Store B? (Test expectation: `FALSE`)
- [ ] **Manager Override:** Can a Finance Manager edit a deal owned by a Sales Rep? (Test expectation: `TRUE`)
- [ ] **Audit Trail Fidelity:** Is every change to `selling_price` recorded in the `audit_trail` array with a `user_id` and `timestamp`?
- [ ] **Agent Restrictions:** Can an AI Agent with "Low Clearance" access the `ssn_token` field? (Test expectation: `FALSE`/`NULL`)

---

## 7. Synthetic Record Volume Recommendations

To simulate a "live" automotive ecosystem for the demo, we recommend generating the following volumes. These numbers are chosen to provide statistical significance for the AI agents without overwhelming a demo environment.

| Dataset | Volume | Rationale |
|---------|--------|-----------|
| Historical Leads | 15,000 | Sufficient to train a small "Lead Scoring" model and show trends over time (e.g., "Leads spike on weekends") |
| Active Inventory | 2,500 | 500 New, 1500 Used, 500 Wholesale. Ensures "Search" agents have enough variation to find matches for specific queries (e.g., "Red Truck under $30k") |
| Customer Profiles | 5,000 | Represents the CRM base. Includes repeat buyers (linked by email/phone) to demonstrate "Customer Lifetime Value" agents |
| Lender Programs | 50 | 10 Lenders × 5 Tiers each. Critical for testing the "Desking" agent's ability to optimize the deal structure (find the best rate) |
| Tax Jurisdictions | 100 | Top 100 US Metros by population. Focus on multi-jurisdiction zip codes (e.g., CO where city/county taxes layer) |
| Compliance Logs | 1,000 | "Pre-filled" audit history to demonstrate the robustness of the governance layer during the demo walkthrough |

---

## 8. Deliverables

The output of this plan is a repository containing the following specific artifacts:

### 8.1 Database Schemas

**SQL DDL / Prisma Schema:** The physical database creation scripts for the Canonical Model (`Customer`, `Inventory`, `Deal`, `ComplianceLog`).

### 8.2 Authorization Configuration

**OpenFGA `model.fga`:** The authorization DSL file defining the User-Deal-Store relationships.

### 8.3 Data Generation Scripts

**Python Generators:** Scripts using `faker` and `numpy` to generate the JSON/CSV files specified in Section 3.

**Requirement:** These scripts must handle the "Logic Constraints" (e.g., ensuring Generated Addresses match Generated Zip Codes).

### 8.4 Validation Notebooks

**Jupyter Notebooks:** Validation notebooks that load the dummy data and run the "Completeness Checklist" assertions (e.g., asserting that Tax calculations match the expected formula for all 50 states).

### 8.5 Agent Prompts

**System Prompts:** Prompts for the AI agents that explain how to interpret the `ComplianceLog` and `DealJacket` schemas (e.g., "You are a Compliance Agent. Your job is to read the `denial_reasons` array and draft a polite, legally compliant letter...").

---

This comprehensive plan provides the blueprints for a robust, compliant, and data-rich environment suitable for high-fidelity automotive retail demonstrations. It moves beyond simple "dummy data" into a structured ecosystem that reflects the real-world complexities of law, finance, and data governance.

---

## References

[^1]: California Trade-In Tax Rules - State Tax Basis Calculation
[^3]: California SB 766 - Offering Price Disclosure Requirements
[^4]: OpenFGA Fine-Grained Authorization Framework
[^5]: SB 478/SB 766 - Drip Pricing Prevention
[^7]: CARS Act - Valueless Add-on Prohibition
[^8]: Valueless Add-on Compliance Validation
[^9]: Regulation B - Adverse Action Reason Codes
[^10]: Adverse Action Notice Generation Requirements
[^11]: FCRA - Written Consent Requirements
[^12]: FCRA Consent Logging Standards
[^13]: Truth in Lending Act - Day Count Conventions
[^14]: Lender-Specific Amortization Methods
[^16]: ADF XML Multi-Lead Handling
[^17]: ADF Lead ID Deduplication
[^18]: US Tax Jurisdiction Database
