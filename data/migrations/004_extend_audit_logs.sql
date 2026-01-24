-- Migration 004: Extend audit_logs table
-- Per 02_strategic_blueprint.md §3.2.2 Regulatory Audit Log Schema

-- Add transaction_id for unique tracking (UUID)
ALTER TABLE audit_logs ADD COLUMN transaction_id TEXT;

-- Add actor to track which agent/user performed the action
ALTER TABLE audit_logs ADD COLUMN actor TEXT;  -- user | agent:conversationalist | agent:fin_calc | agent:compliance

-- Add event_type for categorization
ALTER TABLE audit_logs ADD COLUMN event_type TEXT;  -- rate_inquiry | soft_pull_consent | adverse_action_generated | disclosure_presented

-- Add payload_hash for tamper evidence (SHA-256)
ALTER TABLE audit_logs ADD COLUMN payload_hash TEXT;  -- 64-char hex string

-- Add regulatory_flags for compliance tracking
ALTER TABLE audit_logs ADD COLUMN regulatory_flags TEXT;  -- JSON: {fcra_compliant, sb766_disclosure_verified, adverse_action_reason_code}
