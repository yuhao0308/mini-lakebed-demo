-- Mini-Lakebed Demo Database Schema
-- All data is SYNTHETIC for demonstration purposes only
-- Per 03_implementation_dummy_data_plan.md Canonical Domain Data Model

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Inventory table: Vehicle listings (InventoryUnit)
-- Per 03_implementation_dummy_data_plan.md §1.2
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vin TEXT UNIQUE NOT NULL,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    trim TEXT,
    body_style TEXT NOT NULL,
    exterior_color TEXT,
    interior_color TEXT,
    mileage INTEGER DEFAULT 0,
    price REAL NOT NULL,
    msrp REAL,
    fuel_type TEXT DEFAULT 'gasoline',
    transmission TEXT DEFAULT 'automatic',
    drivetrain TEXT DEFAULT 'FWD',
    engine TEXT,
    status TEXT DEFAULT 'available' CHECK(status IN ('available', 'sold', 'reserved')),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- T01 Extensions: SB 766 compliance fields
    sb766_offering_price REAL,  -- Distinct from price per SB 766
    add_ons TEXT,  -- JSON: [{add_on_id, name, price, benefit_statement, compliance_check_passed}]
    store_id TEXT  -- Multi-location support
);

-- Customers table: CustomerProfile
-- Per 03_implementation_dummy_data_plan.md §1.1
CREATE TABLE IF NOT EXISTS customers (
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

-- Deals table: DealJacket
-- Per 03_implementation_dummy_data_plan.md §1.3
CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,  -- deal_XXXXXX
    customer_id TEXT REFERENCES customers(id),
    vehicle_id INTEGER REFERENCES inventory(id),
    deal_status TEXT CHECK(deal_status IN ('working', 'desked', 'contracted', 'funded', 'unwound')),
    deal_type TEXT CHECK(deal_type IN ('retail_finance', 'lease', 'cash')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Financial Structure
    selling_price REAL,
    rebates_total REAL DEFAULT 0,
    cash_down_payment REAL DEFAULT 0,
    -- Trade-In (JSON)
    trade_in TEXT,  -- JSON: {has_trade, allowance, payoff_amount, equity_amount, negative_equity_financed}
    -- Tax Calculation (JSON)
    tax_calculation TEXT,  -- JSON: {jurisdiction_code, tax_rate_combined, taxable_basis, total_sales_tax, rule_applied}
    -- Fees (JSON)
    fees TEXT,  -- JSON: {doc_fee, license_fee, registration_fee, total_fees}
    -- Lending Terms (JSON)
    lending_terms TEXT,  -- JSON: {lender_id, program_tier, term_months, buy_rate, contract_apr, days_basis, amount_financed, monthly_payment, total_of_payments, finance_charge}
    -- Audit Trail (JSON array)
    audit_trail TEXT  -- JSON: [{timestamp, user_id, action, previous_value, new_value}]
);

-- Lender rules table: Synthetic financing rules
-- Per 02_strategic_blueprint.md §3.2.1 Rate Sheet Schema
CREATE TABLE IF NOT EXISTS lender_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT UNIQUE NOT NULL,
    lender_name TEXT NOT NULL,
    program_name TEXT,
    credit_tier TEXT NOT NULL CHECK(credit_tier IN ('super_prime', 'prime', 'near_prime', 'subprime', 'deep_subprime')),
    min_fico INTEGER NOT NULL,
    max_fico INTEGER NOT NULL,
    min_term_months INTEGER DEFAULT 12,
    max_term_months INTEGER DEFAULT 84,
    base_apr REAL NOT NULL,
    max_ltv REAL NOT NULL DEFAULT 1.20,
    min_loan_amount REAL DEFAULT 5000,
    max_loan_amount REAL DEFAULT 100000,
    doc_fee REAL DEFAULT 0,
    acquisition_fee REAL DEFAULT 0,
    is_demo BOOLEAN DEFAULT TRUE,
    effective_date DATE,
    expiration_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- T01 Extensions: Day count and dealer reserve
    days_basis TEXT DEFAULT '30/360',  -- 30/360 | actual/365 | 365/360
    dealer_reserve_cap REAL DEFAULT 2.5,
    stips_required TEXT  -- JSON array: ["poi", "por", "references"]
);

-- Audit logs table: Request/response logging
-- Per 02_strategic_blueprint.md §3.2.2 Regulatory Audit Log Schema
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    user_input TEXT,
    request_params TEXT,
    response_data TEXT,
    rule_id TEXT,
    calculation_trace TEXT,
    processing_time_ms INTEGER,
    error TEXT,
    -- T01 Extensions: Regulatory audit fields
    transaction_id TEXT,  -- UUID
    actor TEXT,  -- user | agent:conversationalist | agent:fin_calc | agent:compliance
    event_type TEXT,  -- rate_inquiry | soft_pull_consent | adverse_action_generated | disclosure_presented
    payload_hash TEXT,  -- SHA-256 hex (64 chars)
    regulatory_flags TEXT  -- JSON: {fcra_compliant, sb766_disclosure_verified, adverse_action_reason_code}
);

-- Sessions table: Chat session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    messages_count INTEGER DEFAULT 0,
    metadata TEXT
);

-- ============================================================================
-- REFERENCE DATA TABLES
-- ============================================================================

-- Tax rates table: Tax jurisdictions
-- Per 03_implementation_dummy_data_plan.md §3.1.1
CREATE TABLE IF NOT EXISTS tax_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zip_code TEXT NOT NULL,
    state TEXT NOT NULL,
    city TEXT NOT NULL,
    county TEXT NOT NULL,
    county_rate REAL NOT NULL,
    city_rate REAL NOT NULL,
    state_rate REAL NOT NULL,
    combined_rate REAL NOT NULL,
    special_district_rate REAL DEFAULT 0,
    tax_basis_rule TEXT NOT NULL,  -- DESTINATION_BASED | ORIGIN_BASED
    trade_in_credit BOOLEAN NOT NULL  -- FALSE for CA, TRUE for AZ/TX/NV/FL
);

-- Adverse action codes table: Regulation B reason codes
-- Per 03_implementation_dummy_data_plan.md §3.1.3
CREATE TABLE IF NOT EXISTS adverse_action_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,  -- e.g., "A01", "B02"
    text TEXT NOT NULL  -- Full reason text per Reg B
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Inventory indexes
CREATE INDEX IF NOT EXISTS idx_inventory_make ON inventory(make);
CREATE INDEX IF NOT EXISTS idx_inventory_body_style ON inventory(body_style);
CREATE INDEX IF NOT EXISTS idx_inventory_price ON inventory(price);
CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status);
CREATE INDEX IF NOT EXISTS idx_inventory_store_id ON inventory(store_id);

-- Customer indexes
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state);
CREATE INDEX IF NOT EXISTS idx_customers_zip ON customers(zip);

-- Deal indexes
CREATE INDEX IF NOT EXISTS idx_deals_customer_id ON deals(customer_id);
CREATE INDEX IF NOT EXISTS idx_deals_vehicle_id ON deals(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(deal_status);
CREATE INDEX IF NOT EXISTS idx_deals_created_at ON deals(created_at);

-- Lender rules indexes
CREATE INDEX IF NOT EXISTS idx_lender_rules_tier ON lender_rules(credit_tier);
CREATE INDEX IF NOT EXISTS idx_lender_rules_fico ON lender_rules(min_fico, max_fico);
CREATE INDEX IF NOT EXISTS idx_lender_rules_lender ON lender_rules(lender_name);

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_session ON audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_transaction_id ON audit_logs(transaction_id);

-- Tax rates indexes
CREATE INDEX IF NOT EXISTS idx_tax_rates_zip ON tax_rates(zip_code);
CREATE INDEX IF NOT EXISTS idx_tax_rates_state ON tax_rates(state);

-- Adverse action codes indexes
CREATE INDEX IF NOT EXISTS idx_adverse_action_codes_code ON adverse_action_codes(code);
