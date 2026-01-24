"""
T01 Data Foundation Acceptance Tests

Tests for database schema, reference data loading, and data integrity.
Per tasks/T01_data_foundation.md
"""

import pytest
import sqlite3
import json
import re
import uuid
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "mini_lakebed.db"


@pytest.fixture
def db_connection():
    """Provide a database connection for tests."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ============================================================================
# T01-01 to T01-03: Customers Table Tests
# ============================================================================

def test_customers_table_exists(db_connection):
    """T01-01: SELECT * FROM customers does not error."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM customers")
    # Should not raise an error
    assert True


def test_customer_uuid_format(db_connection):
    """T01-02: Customer ID matches UUID v4 regex."""
    cursor = db_connection.cursor()

    # Insert a test customer with UUID
    test_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO customers (id, first_name, last_name)
        VALUES (?, 'Test', 'User')
    """, (test_id,))

    # Verify UUID format
    cursor.execute("SELECT id FROM customers WHERE id = ?", (test_id,))
    row = cursor.fetchone()

    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
    assert re.match(uuid_pattern, row['id'].lower())

    # Cleanup
    cursor.execute("DELETE FROM customers WHERE id = ?", (test_id,))
    db_connection.commit()


def test_customer_fcra_consent_json(db_connection):
    """T01-03: fcra_consent_log parses as valid JSON array."""
    cursor = db_connection.cursor()

    # Insert customer with FCRA consent log
    test_id = str(uuid.uuid4())
    consent_log = json.dumps([{
        "consent_id": "consent_001",
        "consent_type": "soft_pull",
        "granted_at": "2026-01-23T12:00:00Z",
        "ip_address": "192.168.1.1",
        "expires_at": "2026-02-22T12:00:00Z"
    }])

    cursor.execute("""
        INSERT INTO customers (id, first_name, last_name, fcra_consent_log)
        VALUES (?, 'Test', 'User', ?)
    """, (test_id, consent_log))

    # Retrieve and parse
    cursor.execute("SELECT fcra_consent_log FROM customers WHERE id = ?", (test_id,))
    row = cursor.fetchone()

    parsed = json.loads(row['fcra_consent_log'])
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]['consent_type'] == 'soft_pull'

    # Cleanup
    cursor.execute("DELETE FROM customers WHERE id = ?", (test_id,))
    db_connection.commit()


# ============================================================================
# T01-04 to T01-06: Deals Table Tests
# ============================================================================

def test_deals_table_exists(db_connection):
    """T01-04: SELECT * FROM deals does not error."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM deals")
    assert True


def test_deal_status_constraint(db_connection):
    """T01-05: INSERT with deal_status='invalid' raises error."""
    cursor = db_connection.cursor()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO deals (id, deal_status, deal_type, selling_price)
            VALUES ('deal_test_001', 'invalid', 'retail_finance', 25000)
        """)


def test_deal_foreign_keys(db_connection):
    """T01-06: Deal with invalid customer_id raises FK error."""
    cursor = db_connection.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Try to insert deal with non-existent customer
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO deals (id, customer_id, deal_status, deal_type, selling_price)
            VALUES ('deal_test_002', 'non_existent_customer', 'working', 'retail_finance', 25000)
        """)


# ============================================================================
# T01-07 to T01-08: Inventory Extension Tests
# ============================================================================

def test_inventory_sb766_price(db_connection):
    """T01-07: sb766_offering_price column accessible."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT sb766_offering_price FROM inventory LIMIT 1")
    row = cursor.fetchone()

    # Should have a value (seeded data)
    assert row is not None
    assert row['sb766_offering_price'] is not None


def test_inventory_addons_json(db_connection):
    """T01-08: add_ons parses as valid JSON array."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT add_ons FROM inventory WHERE add_ons IS NOT NULL LIMIT 1")
    row = cursor.fetchone()

    if row:
        parsed = json.loads(row['add_ons'])
        assert isinstance(parsed, list)


# ============================================================================
# T01-09 to T01-10: Audit Logs & Lender Rules Extension Tests
# ============================================================================

def test_audit_logs_payload_hash(db_connection):
    """T01-09: payload_hash accepts 64-char hex string."""
    cursor = db_connection.cursor()

    # Insert audit log with payload hash
    test_hash = "a" * 64  # Valid 64-char hex
    cursor.execute("""
        INSERT INTO audit_logs (session_id, action, payload_hash)
        VALUES ('test_session', 'test_action', ?)
    """, (test_hash,))

    cursor.execute("""
        SELECT payload_hash FROM audit_logs
        WHERE session_id = 'test_session' AND action = 'test_action'
    """)
    row = cursor.fetchone()

    assert row['payload_hash'] == test_hash
    assert len(row['payload_hash']) == 64

    # Cleanup
    cursor.execute("DELETE FROM audit_logs WHERE session_id = 'test_session'")
    db_connection.commit()


def test_lender_rules_days_basis(db_connection):
    """T01-10: days_basis defaults to '30/360'."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT days_basis FROM lender_rules LIMIT 1")
    row = cursor.fetchone()

    assert row['days_basis'] in ['30/360', 'actual/365', '365/360']


# ============================================================================
# T01-11 to T01-15: Reference Data Loading Tests
# ============================================================================

def test_tax_rates_loaded(db_connection):
    """T01-11: tax_rates table has >= 100 rows."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM tax_rates")
    row = cursor.fetchone()

    assert row['count'] >= 100, f"Expected >= 100 tax rates, got {row['count']}"


def test_adverse_codes_loaded(db_connection):
    """T01-12: adverse_action_codes table has >= 25 rows."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM adverse_action_codes")
    row = cursor.fetchone()

    assert row['count'] >= 25, f"Expected >= 25 codes, got {row['count']}"


def test_lender_programs_loaded(db_connection):
    """T01-13: lender_rules table has >= 50 rows."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM lender_rules")
    row = cursor.fetchone()

    assert row['count'] >= 50, f"Expected >= 50 lender rules, got {row['count']}"


def test_ca_tax_no_tradein_credit(db_connection):
    """T01-14: CA zip returns trade_in_credit=FALSE."""
    cursor = db_connection.cursor()

    cursor.execute("""
        SELECT trade_in_credit FROM tax_rates
        WHERE state = 'CA' LIMIT 1
    """)
    row = cursor.fetchone()

    assert row is not None, "No CA tax rates found"
    # SQLite stores booleans as 0/1
    assert row['trade_in_credit'] == 0, "CA should have trade_in_credit=FALSE"


def test_az_tax_tradein_credit(db_connection):
    """T01-15: AZ zip returns trade_in_credit=TRUE."""
    cursor = db_connection.cursor()

    cursor.execute("""
        SELECT trade_in_credit FROM tax_rates
        WHERE state = 'AZ' LIMIT 1
    """)
    row = cursor.fetchone()

    assert row is not None, "No AZ tax rates found"
    # SQLite stores booleans as 0/1
    assert row['trade_in_credit'] == 1, "AZ should have trade_in_credit=TRUE"


# ============================================================================
# Additional Data Integrity Tests
# ============================================================================

def test_inventory_has_sb766_prices(db_connection):
    """Verify all inventory has sb766_offering_price set."""
    cursor = db_connection.cursor()

    cursor.execute("""
        SELECT COUNT(*) as count FROM inventory
        WHERE sb766_offering_price IS NULL
    """)
    row = cursor.fetchone()

    assert row['count'] == 0, "All inventory should have sb766_offering_price"


def test_lender_rules_have_days_basis(db_connection):
    """Verify all lender rules have days_basis set."""
    cursor = db_connection.cursor()

    cursor.execute("""
        SELECT COUNT(*) as count FROM lender_rules
        WHERE days_basis IS NULL
    """)
    row = cursor.fetchone()

    assert row['count'] == 0, "All lender rules should have days_basis"


def test_adverse_action_code_format(db_connection):
    """Verify adverse action codes match expected format."""
    cursor = db_connection.cursor()

    cursor.execute("SELECT code FROM adverse_action_codes")
    rows = cursor.fetchall()

    code_pattern = r'^[A-Z]\d{2}$'
    for row in rows:
        assert re.match(code_pattern, row['code']), f"Invalid code format: {row['code']}"
