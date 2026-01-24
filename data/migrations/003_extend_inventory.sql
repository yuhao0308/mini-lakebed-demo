-- Migration 003: Extend inventory table
-- Per 03_implementation_dummy_data_plan.md §1.2 InventoryUnit
-- Adds SB 766 offering price and add-ons support

-- Add sb766_offering_price column (distinct from price per SB 766)
ALTER TABLE inventory ADD COLUMN sb766_offering_price REAL;

-- Add add_ons JSON column for tracking vehicle add-ons with benefit statements
ALTER TABLE inventory ADD COLUMN add_ons TEXT;  -- JSON: [{add_on_id, name, price, benefit_statement, compliance_check_passed}]

-- Add store_id for multi-location support
ALTER TABLE inventory ADD COLUMN store_id TEXT;

-- Update existing records to set sb766_offering_price = price (default)
UPDATE inventory SET sb766_offering_price = price WHERE sb766_offering_price IS NULL;
