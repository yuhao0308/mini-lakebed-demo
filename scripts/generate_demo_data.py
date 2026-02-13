"""
T06: Generate Demo Data

Generate pre-filled demo data for UAT walkthroughs.

Per spec §7: 1,000 compliance logs for demo environment.
Per tasks/T06_demo_polish.md
"""

import argparse
import json
import random
import uuid
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Sequence

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "mini_lakebed.db"

# First/last names for synthetic data
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker"
]

# Event types for compliance logs
EVENT_TYPES = [
    "sb766_disclosure_verified",
    "soft_pull_consent",
    "adverse_action_generated",
    "disclosure_presented",
    "rate_inquiry",
    "payment_estimate"
]

# Adverse action reason codes
ADVERSE_REASON_CODES = [
    ("A01", "Too many inquiries in the last 12 months"),
    ("A12", "Length of time accounts have been established"),
    ("B02", "Amount owed on revolving accounts is too high"),
    ("B12", "Proportion of balances to credit limits is too high"),
    ("C03", "Too few bank revolving accounts"),
    ("C12", "Length of time since delinquency is too recent"),
    ("D04", "Too many bank or national revolving accounts with balances"),
    ("D12", "Lack of recent bank revolving information")
]

# Credit tiers and FICO ranges
CREDIT_TIERS = {
    "super_prime": (750, 850),
    "prime": (700, 749),
    "near_prime": (650, 699),
    "subprime": (600, 649),
    "deep_subprime": (300, 599)
}


def generate_uuid() -> str:
    """Generate UUID v4."""
    return str(uuid.uuid4())


def random_date(start_days_ago: int = 365, end_days_ago: int = 0) -> str:
    """
    Generate random date within range.

    Positive values = past dates (days ago)
    Negative values = future dates (days ahead)
    """
    min_days = min(start_days_ago, end_days_ago)
    max_days = max(start_days_ago, end_days_ago)
    days_ago = random.randint(min_days, max_days)
    date = datetime.now() - timedelta(days=days_ago)
    return date.strftime("%Y-%m-%d %H:%M:%S")


def generate_compliance_logs(count: int = 1000) -> List[Dict[str, Any]]:
    """
    Generate realistic compliance log entries.

    Distribution:
    - 60% successful disclosures (sb766_disclosure_verified: true)
    - 25% soft_pull_consent events
    - 10% adverse_action_generated
    - 5% disclosure_presented (other types)

    Args:
        count: Number of logs to generate

    Returns:
        List of compliance log dictionaries
    """
    logs = []

    # Distribution weights
    event_weights = {
        "sb766_disclosure_verified": 0.60,
        "soft_pull_consent": 0.25,
        "adverse_action_generated": 0.10,
        "disclosure_presented": 0.03,
        "rate_inquiry": 0.01,
        "payment_estimate": 0.01
    }

    for i in range(count):
        # Select event type based on weights
        event_type = random.choices(
            list(event_weights.keys()),
            weights=list(event_weights.values())
        )[0]

        # Generate session and transaction IDs
        session_id = f"session_{generate_uuid()[:8]}"
        transaction_id = generate_uuid()

        # Generate actor (user or agent)
        actor_types = ["user", "agent:conversationalist", "agent:fin_calc", "agent:compliance"]
        actor = random.choice(actor_types)

        # Generate timestamp
        timestamp = random_date(365, 0)

        # Generate regulatory flags based on event type
        regulatory_flags = {}
        if event_type == "sb766_disclosure_verified":
            regulatory_flags = {
                "fcra_compliant": True,
                "sb766_disclosure_verified": True,
                "offering_price_displayed": True
            }
        elif event_type == "soft_pull_consent":
            regulatory_flags = {
                "fcra_compliant": True,
                "consent_recorded": True,
                "ip_address_logged": True
            }
        elif event_type == "adverse_action_generated":
            reasons = random.sample(ADVERSE_REASON_CODES, min(4, random.randint(2, 4)))
            regulatory_flags = {
                "fcra_compliant": True,
                "adverse_action_reason_codes": [r[0] for r in reasons],
                "reg_b_compliant": True
            }
        else:
            regulatory_flags = {"fcra_compliant": True}

        log = {
            "session_id": session_id,
            "timestamp": timestamp,
            "action": event_type,
            "transaction_id": transaction_id,
            "actor": actor,
            "event_type": event_type,
            "payload_hash": generate_uuid().replace("-", "")[:64],
            "regulatory_flags": json.dumps(regulatory_flags)
        }

        logs.append(log)

    return logs


def generate_demo_customers(count: int = 100) -> List[Dict[str, Any]]:
    """
    Generate demo customers with varied credit profiles.

    Distribution per spec §3.2.1:
    - 60% Prime (Score > 700)
    - 30% Subprime (Score < 620)
    - 10% Edge cases

    Args:
        count: Number of customers to generate

    Returns:
        List of customer dictionaries
    """
    customers = []

    # Calculate distribution
    prime_count = int(count * 0.60)
    subprime_count = int(count * 0.30)
    edge_count = count - prime_count - subprime_count

    # States for variety
    states = ["CA", "TX", "AZ", "NV", "FL"]

    for i in range(count):
        customer_id = f"cust_{generate_uuid()[:8]}"

        # Determine tier based on position
        if i < prime_count:
            tier = random.choice(["super_prime", "prime"])
        elif i < prime_count + subprime_count:
            tier = random.choice(["subprime", "deep_subprime"])
        else:
            tier = random.choice(["near_prime", "prime"])

        # Generate FICO in tier range
        fico_range = CREDIT_TIERS[tier]
        fico = random.randint(fico_range[0], fico_range[1])

        # Generate name
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        # Generate other fields
        state = random.choice(states)
        dob = f"19{random.randint(60, 99)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        income = random.randint(3000, 15000)

        # SSN masked
        ssn_last4 = f"{random.randint(1000, 9999)}"
        ssn_masked = f"***-**-{ssn_last4}"

        # FCRA consent
        consent = [{
            "consent_id": generate_uuid(),
            "type": "soft_pull",
            "granted_at": random_date(30, 0),
            "ip_address": f"192.168.1.{random.randint(1, 254)}",
            "expires_at": random_date(-30, -1)  # Future date
        }]

        customer = {
            "id": customer_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "phone_primary": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "date_of_birth": dob,
            "ssn_masked": ssn_masked,
            "ssn_token": f"vault_{generate_uuid()[:12]}",
            "state": state,
            "city": f"{state} City",
            "zip": f"{random.randint(10000, 99999)}",
            "residence_type": random.choice(["own", "rent"]),
            "monthly_gross_income": income,
            "pii_clearance_level": "low",
            "fcra_consent_log": json.dumps(consent),
            "created_at": random_date(365, 30),
            "source_system": "demo"
        }

        customers.append(customer)

    return customers


def generate_demo_deals(
    count: int = 50,
    customer_ids: Optional[Sequence[str]] = None,
    vehicle_ids: Optional[Sequence[int]] = None
) -> List[Dict[str, Any]]:
    """
    Generate demo deals in various states.

    Distribution:
    - 20 working
    - 15 desked
    - 10 contracted
    - 5 funded

    Args:
        count: Number of deals to generate

    Returns:
        List of deal dictionaries
    """
    deals = []

    # Status distribution
    statuses = (
        ["working"] * 20 +
        ["desked"] * 15 +
        ["contracted"] * 10 +
        ["funded"] * 5
    )

    # Ensure we have enough statuses
    while len(statuses) < count:
        statuses.append(random.choice(["working", "desked", "contracted"]))

    random.shuffle(statuses)

    resolved_customer_ids = list(customer_ids) if customer_ids else []
    resolved_vehicle_ids = [int(v) for v in vehicle_ids] if vehicle_ids else []

    for i in range(count):
        deal_id = f"deal_{generate_uuid()[:8]}"
        status = statuses[i] if i < len(statuses) else "working"

        # Reference existing IDs when available to keep demo data coherent.
        customer_id = (
            random.choice(resolved_customer_ids)
            if resolved_customer_ids
            else f"cust_{generate_uuid()[:8]}"
        )
        vehicle_id = (
            random.choice(resolved_vehicle_ids)
            if resolved_vehicle_ids
            else random.randint(1, max(20, count))
        )

        # Generate financial structure
        selling_price = random.randint(20000, 50000)
        down_payment = random.randint(0, 10000)
        tax_rate = random.uniform(0.06, 0.10)
        tax_amount = selling_price * tax_rate

        # Fees
        fees = {
            "doc_fee": 85,
            "license_fee": random.randint(100, 300),
            "registration_fee": random.randint(50, 150),
            "total_fees": 0
        }
        fees["total_fees"] = fees["doc_fee"] + fees["license_fee"] + fees["registration_fee"]

        # Tax calculation
        tax_calc = {
            "jurisdiction_code": random.choice(["CA", "TX", "AZ"]),
            "tax_rate_combined": tax_rate,
            "taxable_basis": selling_price,
            "total_sales_tax": tax_amount,
            "rule_applied": "destination_based"
        }

        # Lending terms
        term = random.choice([48, 60, 72])
        apr = random.uniform(4.0, 12.0)
        amount_financed = selling_price + tax_amount + fees["total_fees"] - down_payment
        monthly_rate = apr / 100 / 12
        monthly_payment = (amount_financed * monthly_rate) / (1 - (1 + monthly_rate) ** -term)

        lending_terms = {
            "lender_id": f"LENDER_{random.randint(1, 5)}",
            "program_tier": random.choice(["super_prime", "prime", "near_prime"]),
            "term_months": term,
            "buy_rate": apr - 1,
            "contract_apr": apr,
            "days_basis": "30/360",
            "amount_financed": amount_financed,
            "monthly_payment": round(monthly_payment, 2),
            "total_of_payments": round(monthly_payment * term, 2),
            "finance_charge": round(monthly_payment * term - amount_financed, 2)
        }

        # Audit trail
        audit_trail = [{
            "timestamp": random_date(30, 0),
            "user_id": f"user_{random.randint(1, 10)}",
            "action": "deal_created",
            "previous_value": None,
            "new_value": {"status": "working"}
        }]

        deal = {
            "id": deal_id,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "deal_status": status,
            "deal_type": random.choice(["retail_finance", "lease", "cash"]),
            "selling_price": selling_price,
            "rebates_total": random.randint(0, 2000),
            "cash_down_payment": down_payment,
            "trade_in": json.dumps({"has_trade": False}),
            "tax_calculation": json.dumps(tax_calc),
            "fees": json.dumps(fees),
            "lending_terms": json.dumps(lending_terms),
            "audit_trail": json.dumps(audit_trail),
            "created_at": random_date(90, 0)
        }

        deals.append(deal)

    return deals


def insert_compliance_logs(conn: sqlite3.Connection, logs: List[Dict[str, Any]]) -> int:
    """Insert compliance logs into database."""
    cursor = conn.cursor()
    inserted = 0

    for log in logs:
        cursor.execute("""
            INSERT INTO audit_logs (
                session_id, timestamp, action, transaction_id,
                actor, event_type, payload_hash, regulatory_flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log["session_id"],
            log["timestamp"],
            log["action"],
            log["transaction_id"],
            log["actor"],
            log["event_type"],
            log["payload_hash"],
            log["regulatory_flags"]
        ))
        inserted += 1

    conn.commit()
    print(f"Inserted {inserted} compliance logs")
    return inserted


def insert_customers(conn: sqlite3.Connection, customers: List[Dict[str, Any]]) -> int:
    """Insert demo customers into database."""
    cursor = conn.cursor()
    inserted = 0

    for customer in customers:
        try:
            cursor.execute("""
                INSERT INTO customers (
                    id, first_name, last_name, email, phone_primary,
                    date_of_birth, ssn_masked, ssn_token, state, city, zip,
                    residence_type, monthly_gross_income, pii_clearance_level,
                    fcra_consent_log, created_at, source_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer["id"],
                customer["first_name"],
                customer["last_name"],
                customer["email"],
                customer["phone_primary"],
                customer["date_of_birth"],
                customer["ssn_masked"],
                customer["ssn_token"],
                customer["state"],
                customer["city"],
                customer["zip"],
                customer["residence_type"],
                customer["monthly_gross_income"],
                customer["pii_clearance_level"],
                customer["fcra_consent_log"],
                customer["created_at"],
                customer["source_system"]
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Skip if customer already exists
            pass

    conn.commit()
    print(f"Inserted {inserted} demo customers")
    return inserted


def insert_deals(conn: sqlite3.Connection, deals: List[Dict[str, Any]]) -> int:
    """Insert demo deals into database."""
    cursor = conn.cursor()
    inserted = 0

    for deal in deals:
        try:
            cursor.execute("""
                INSERT INTO deals (
                    id, customer_id, vehicle_id, deal_status, deal_type,
                    selling_price, rebates_total, cash_down_payment,
                    trade_in, tax_calculation, fees, lending_terms,
                    audit_trail, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal["id"],
                deal["customer_id"],
                deal["vehicle_id"],
                deal["deal_status"],
                deal["deal_type"],
                deal["selling_price"],
                deal["rebates_total"],
                deal["cash_down_payment"],
                deal["trade_in"],
                deal["tax_calculation"],
                deal["fees"],
                deal["lending_terms"],
                deal["audit_trail"],
                deal["created_at"]
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Skip if deal already exists
            pass

    conn.commit()
    print(f"Inserted {inserted} demo deals")
    return inserted


def _fetch_available_vehicle_ids(conn: sqlite3.Connection) -> List[int]:
    """Return available inventory IDs to link demo deals to real vehicles."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM inventory WHERE status = 'available' ORDER BY id")
    return [int(row[0]) for row in cursor.fetchall()]


def seed_demo_data(
    conn: sqlite3.Connection,
    compliance_log_count: int = 1000,
    customer_count: int = 100,
    deal_count: int = 50,
    reset_existing: bool = True
) -> Dict[str, int]:
    """
    Seed demo logs/customers/deals into an existing database connection.

    Args:
        conn: Open SQLite connection.
        compliance_log_count: Number of audit/compliance logs to generate.
        customer_count: Number of synthetic customers to generate.
        deal_count: Number of synthetic deals to generate.
        reset_existing: If True, clear existing demo tables before seeding.

    Returns:
        Summary counts of inserted rows.
    """
    cursor = conn.cursor()

    if reset_existing:
        cursor.execute("DELETE FROM deals")
        cursor.execute("DELETE FROM customers")
        cursor.execute("DELETE FROM audit_logs")
        conn.commit()
        print("Cleared existing deals/customers/audit_logs")

    print(f"\nGenerating {compliance_log_count:,} compliance logs...")
    logs = generate_compliance_logs(compliance_log_count)
    inserted_logs = insert_compliance_logs(conn, logs)

    print(f"\nGenerating {customer_count:,} demo customers...")
    customers = generate_demo_customers(customer_count)
    inserted_customers = insert_customers(conn, customers)

    available_vehicle_ids = _fetch_available_vehicle_ids(conn)
    if not available_vehicle_ids:
        print("Warning: No available vehicles found; generated deals use fallback IDs.")

    print(f"\nGenerating {deal_count:,} demo deals...")
    deals = generate_demo_deals(
        deal_count,
        customer_ids=[c["id"] for c in customers],
        vehicle_ids=available_vehicle_ids
    )
    inserted_deals = insert_deals(conn, deals)

    return {
        "compliance_logs": inserted_logs,
        "customers": inserted_customers,
        "deals": inserted_deals
    }


def main():
    """Generate and insert demo data into an existing Mini-Lakebed database."""
    parser = argparse.ArgumentParser(description="Generate demo logs/customers/deals.")
    parser.add_argument(
        "--compliance-logs",
        type=int,
        default=1000,
        help="Number of compliance logs to generate (default: 1000)"
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=100,
        help="Number of demo customers to generate (default: 100)"
    )
    parser.add_argument(
        "--deals",
        type=int,
        default=50,
        help="Number of demo deals to generate (default: 50)"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing demo tables instead of clearing them first"
    )
    args = parser.parse_args()

    print(f"Database path: {DB_PATH}")

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Run 'python -m scripts.seed_data' first to create the database.")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        summary = seed_demo_data(
            conn=conn,
            compliance_log_count=args.compliance_logs,
            customer_count=args.customers,
            deal_count=args.deals,
            reset_existing=not args.append
        )

        print("\nDemo data generation complete!")
        print("Summary:")
        print(
            f"  - {summary['compliance_logs']:,} compliance logs "
            "(~60% disclosures, ~25% consents, ~10% adverse actions)"
        )
        print(
            f"  - {summary['customers']:,} demo customers "
            "(60% prime, 30% subprime, 10% edge)"
        )
        print(
            f"  - {summary['deals']:,} demo deals "
            "(working/desked/contracted/funded mix)"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
