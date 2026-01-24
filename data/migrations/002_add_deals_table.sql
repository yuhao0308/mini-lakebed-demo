-- Migration 002: Add deals table
-- Per 03_implementation_dummy_data_plan.md §1.3 DealJacket

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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_deals_customer_id ON deals(customer_id);
CREATE INDEX IF NOT EXISTS idx_deals_vehicle_id ON deals(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(deal_status);
CREATE INDEX IF NOT EXISTS idx_deals_created_at ON deals(created_at);
