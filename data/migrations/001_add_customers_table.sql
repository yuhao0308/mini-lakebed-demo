-- Migration 001: Add customers table
-- Per 03_implementation_dummy_data_plan.md §1.1 CustomerProfile

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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state);
CREATE INDEX IF NOT EXISTS idx_customers_zip ON customers(zip);
