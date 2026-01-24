-- Migration 005: Extend lender_rules table
-- Per 02_strategic_blueprint.md §3.2.1 Vehicle Rate Sheet Schema
-- Per 03_implementation_dummy_data_plan.md §4.1 Interest Calculation Algorithms

-- Add days_basis for interest calculation method
ALTER TABLE lender_rules ADD COLUMN days_basis TEXT DEFAULT '30/360';  -- 30/360 | actual/365 | 365/360

-- Add dealer_reserve_cap for maximum dealer markup
ALTER TABLE lender_rules ADD COLUMN dealer_reserve_cap REAL DEFAULT 2.5;

-- Add stips_required for stipulations
ALTER TABLE lender_rules ADD COLUMN stips_required TEXT;  -- JSON array: ["poi", "por", "references"]
