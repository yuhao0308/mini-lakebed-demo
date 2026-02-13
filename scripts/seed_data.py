"""
Seed data generator for Mini-Lakebed Demo.

Generates synthetic vehicles and lender rules for demonstration.
All data is clearly labeled as DEMO ONLY.

T01 Enhancement: Loads reference data (tax rates, adverse action codes, lender programs)
"""

import argparse
import sqlite3
import random
import json
import csv
from pathlib import Path
from datetime import datetime

# Paths
BASE_PATH = Path(__file__).parent.parent
DB_PATH = BASE_PATH / "data" / "mini_lakebed.db"
SCHEMA_PATH = BASE_PATH / "data" / "schema.sql"
MIGRATIONS_PATH = BASE_PATH / "data" / "migrations"
REFERENCE_PATH = BASE_PATH / "data" / "reference"

DEFAULT_INVENTORY_COUNT = 1200
DEFAULT_DEMO_CUSTOMER_COUNT = 100
DEFAULT_DEMO_DEAL_COUNT = 50
DEFAULT_DEMO_LOG_COUNT = 1000


# Synthetic vehicle data
MAKES_MODELS = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Highlander", "Tacoma", "Tundra"],
    "Honda": ["Accord", "Civic", "CR-V", "Pilot", "Odyssey", "HR-V"],
    "Ford": ["F-150", "Mustang", "Explorer", "Escape", "Bronco", "Edge"],
    "Chevrolet": ["Silverado", "Malibu", "Equinox", "Tahoe", "Traverse", "Camaro"],
    "Nissan": ["Altima", "Rogue", "Sentra", "Pathfinder", "Frontier", "Maxima"],
    "Hyundai": ["Elantra", "Sonata", "Tucson", "Santa Fe", "Palisade", "Kona"],
    "Kia": ["Optima", "Sorento", "Sportage", "Telluride", "Forte", "Soul"],
    "BMW": ["3 Series", "5 Series", "X3", "X5", "X1"],
    "Mercedes-Benz": ["C-Class", "E-Class", "GLC", "GLE"],
    "Audi": ["A4", "A6", "Q5", "Q7"],
}

BODY_STYLES = {
    "Camry": "sedan", "Corolla": "sedan", "RAV4": "suv", "Highlander": "suv",
    "Tacoma": "truck", "Tundra": "truck", "Accord": "sedan", "Civic": "sedan",
    "CR-V": "suv", "Pilot": "suv", "Odyssey": "van", "HR-V": "suv",
    "F-150": "truck", "Mustang": "coupe", "Explorer": "suv", "Escape": "suv",
    "Bronco": "suv", "Edge": "suv", "Silverado": "truck", "Malibu": "sedan",
    "Equinox": "suv", "Tahoe": "suv", "Traverse": "suv", "Camaro": "coupe",
    "Altima": "sedan", "Rogue": "suv", "Sentra": "sedan", "Pathfinder": "suv",
    "Frontier": "truck", "Maxima": "sedan", "Elantra": "sedan", "Sonata": "sedan",
    "Tucson": "suv", "Santa Fe": "suv", "Palisade": "suv", "Kona": "suv",
    "Optima": "sedan", "Sorento": "suv", "Sportage": "suv", "Telluride": "suv",
    "Forte": "sedan", "Soul": "hatchback", "3 Series": "sedan", "5 Series": "sedan",
    "X3": "suv", "X5": "suv", "X1": "suv", "C-Class": "sedan", "E-Class": "sedan",
    "GLC": "suv", "GLE": "suv", "A4": "sedan", "A6": "sedan", "Q5": "suv", "Q7": "suv",
}

COLORS = ["Black", "White", "Silver", "Gray", "Red", "Blue", "Green", "Brown", "Beige"]
INTERIOR_COLORS = ["Black", "Gray", "Tan", "Brown", "Beige"]
TRIMS = ["Base", "LE", "SE", "XLE", "Sport", "Limited", "Touring", "Premium"]
FUEL_TYPES = ["gasoline", "gasoline", "gasoline", "hybrid", "electric"]
DRIVETRAINS = ["FWD", "AWD", "RWD", "4WD"]


def generate_vin():
    """Generate a synthetic VIN-like string."""
    chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    return "".join(random.choices(chars, k=17))


def generate_vehicles(count: int = 60):
    """Generate synthetic vehicle inventory."""
    vehicles = []

    for i in range(count):
        make = random.choice(list(MAKES_MODELS.keys()))
        model = random.choice(MAKES_MODELS[make])
        year = random.randint(2019, 2024)

        # Price based on make (luxury brands more expensive)
        if make in ["BMW", "Mercedes-Benz", "Audi"]:
            base_price = random.randint(35000, 65000)
        else:
            base_price = random.randint(18000, 45000)

        # Adjust for year
        price = base_price - (2024 - year) * random.randint(1500, 3000)
        price = max(price, 8000) + random.randint(0, 1500)  # Lower floor + jitter

        mileage = (2024 - year) * random.randint(8000, 15000)

        # T01: Calculate sb766_offering_price (price + doc fee)
        doc_fee = 85.0  # Standard CA doc fee
        sb766_price = round(price, -2) + doc_fee

        vehicles.append({
            "vin": generate_vin(),
            "make": make,
            "model": model,
            "year": year,
            "trim": random.choice(TRIMS),
            "body_style": BODY_STYLES.get(model, "sedan"),
            "exterior_color": random.choice(COLORS),
            "interior_color": random.choice(INTERIOR_COLORS),
            "mileage": mileage,
            "price": round(price, -1),  # Round to nearest 10 to avoid artificial clustering
            "msrp": round(price * 1.15, -2),
            "fuel_type": random.choice(FUEL_TYPES),
            "transmission": "automatic",
            "drivetrain": random.choice(DRIVETRAINS),
            "engine": f"{random.choice(['2.0L', '2.5L', '3.0L', '3.5L'])} {random.choice(['4-Cylinder', 'V6'])}",
            "status": "available",
            "description": f"{year} {make} {model} in excellent condition.",
            # T01: New fields
            "sb766_offering_price": sb766_price,
            "add_ons": json.dumps([]),  # Empty add-ons by default
            "store_id": "store_demo_01"
        })

    return vehicles


def generate_lender_rules():
    """Generate synthetic lender rules. DEMO ONLY."""
    rules = [
        # Super Prime (750-850)
        {"rule_id": "SYNTH-SPRIME-48", "lender_name": "Demo Capital", "program_name": "Premium Auto",
         "credit_tier": "super_prime", "min_fico": 750, "max_fico": 850,
         "min_term_months": 24, "max_term_months": 48, "base_apr": 4.49, "max_ltv": 1.10},
        {"rule_id": "SYNTH-SPRIME-60", "lender_name": "Demo Capital", "program_name": "Premium Auto",
         "credit_tier": "super_prime", "min_fico": 750, "max_fico": 850,
         "min_term_months": 48, "max_term_months": 60, "base_apr": 4.99, "max_ltv": 1.10},
        {"rule_id": "SYNTH-SPRIME-72", "lender_name": "Demo Capital", "program_name": "Premium Auto",
         "credit_tier": "super_prime", "min_fico": 750, "max_fico": 850,
         "min_term_months": 60, "max_term_months": 72, "base_apr": 5.49, "max_ltv": 1.05},

        # Prime (700-749)
        {"rule_id": "SYNTH-PRIME-48", "lender_name": "Demo Capital", "program_name": "Standard Auto",
         "credit_tier": "prime", "min_fico": 700, "max_fico": 749,
         "min_term_months": 24, "max_term_months": 48, "base_apr": 5.99, "max_ltv": 1.15},
        {"rule_id": "SYNTH-PRIME-60", "lender_name": "Demo Capital", "program_name": "Standard Auto",
         "credit_tier": "prime", "min_fico": 700, "max_fico": 749,
         "min_term_months": 48, "max_term_months": 60, "base_apr": 6.49, "max_ltv": 1.10},
        {"rule_id": "SYNTH-PRIME-72", "lender_name": "Demo Capital", "program_name": "Standard Auto",
         "credit_tier": "prime", "min_fico": 700, "max_fico": 749,
         "min_term_months": 60, "max_term_months": 72, "base_apr": 6.99, "max_ltv": 1.05},

        # Near Prime (650-699)
        {"rule_id": "SYNTH-NPRIME-48", "lender_name": "Demo Capital", "program_name": "Access Auto",
         "credit_tier": "near_prime", "min_fico": 650, "max_fico": 699,
         "min_term_months": 24, "max_term_months": 48, "base_apr": 8.99, "max_ltv": 1.05},
        {"rule_id": "SYNTH-NPRIME-60", "lender_name": "Demo Capital", "program_name": "Access Auto",
         "credit_tier": "near_prime", "min_fico": 650, "max_fico": 699,
         "min_term_months": 48, "max_term_months": 60, "base_apr": 9.99, "max_ltv": 1.00},

        # Subprime (580-649)
        {"rule_id": "SYNTH-SUBPRIME-48", "lender_name": "Demo Capital", "program_name": "Fresh Start",
         "credit_tier": "subprime", "min_fico": 580, "max_fico": 649,
         "min_term_months": 24, "max_term_months": 48, "base_apr": 12.99, "max_ltv": 0.90},
        {"rule_id": "SYNTH-SUBPRIME-60", "lender_name": "Demo Capital", "program_name": "Fresh Start",
         "credit_tier": "subprime", "min_fico": 580, "max_fico": 649,
         "min_term_months": 48, "max_term_months": 60, "base_apr": 14.99, "max_ltv": 0.85},
    ]

    # Add common fields
    for rule in rules:
        rule["min_loan_amount"] = 5000
        rule["max_loan_amount"] = 75000
        rule["doc_fee"] = 495
        rule["acquisition_fee"] = 0
        rule["is_demo"] = True
        rule["effective_date"] = "2024-01-01"
        rule["expiration_date"] = None
        # T01: New fields
        rule["days_basis"] = "30/360"
        rule["dealer_reserve_cap"] = 2.5
        rule["stips_required"] = None

    return rules


def run_migrations(cursor):
    """Run database migrations from the migrations directory."""
    if not MIGRATIONS_PATH.exists():
        print("No migrations directory found, skipping migrations")
        return

    migration_files = sorted(MIGRATIONS_PATH.glob("*.sql"))
    for migration_file in migration_files:
        print(f"Running migration: {migration_file.name}")
        try:
            with open(migration_file, "r") as f:
                cursor.executescript(f.read())
        except sqlite3.OperationalError as e:
            # Ignore "duplicate column" errors for ALTER TABLE
            if "duplicate column name" in str(e).lower():
                print(f"  Skipping (column already exists)")
            else:
                raise


def load_tax_rates(cursor):
    """Load tax rates from reference data."""
    tax_rates_path = REFERENCE_PATH / "tax_rates.csv"
    if not tax_rates_path.exists():
        print("No tax_rates.csv found, skipping")
        return 0

    # Clear existing data
    cursor.execute("DELETE FROM tax_rates")

    count = 0
    with open(tax_rates_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO tax_rates (
                    zip_code, state, city, county, county_rate, city_rate,
                    state_rate, combined_rate, special_district_rate,
                    tax_basis_rule, trade_in_credit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["zip_code"],
                row["state"],
                row["city"],
                row["county"],
                float(row["county_rate"]),
                float(row["city_rate"]),
                float(row["state_rate"]),
                float(row["combined_rate"]),
                float(row["special_district_rate"]),
                row["tax_basis_rule"],
                row["trade_in_credit"].upper() == "TRUE"
            ))
            count += 1

    return count


def load_adverse_action_codes(cursor):
    """Load adverse action codes from reference data."""
    codes_path = REFERENCE_PATH / "adverse_action_codes.json"
    if not codes_path.exists():
        print("No adverse_action_codes.json found, skipping")
        return 0

    # Clear existing data
    cursor.execute("DELETE FROM adverse_action_codes")

    with open(codes_path, "r") as f:
        codes = json.load(f)

    for code in codes:
        cursor.execute("""
            INSERT INTO adverse_action_codes (code, text)
            VALUES (?, ?)
        """, (code["code"], code["text"]))

    return len(codes)


def load_lender_programs(cursor):
    """Load lender programs from reference data and insert as lender_rules."""
    programs_path = REFERENCE_PATH / "lender_programs.json"
    if not programs_path.exists():
        print("No lender_programs.json found, skipping")
        return 0

    with open(programs_path, "r") as f:
        lenders = json.load(f)

    count = 0
    tier_mapping = {
        "S": "super_prime",
        "A": "prime",
        "B": "near_prime",
        "C": "subprime",
        "D": "deep_subprime"
    }

    for lender in lenders:
        lender_id = lender["lender_id"]
        lender_name = lender["lender_name"]
        effective_date = lender["effective_date"]

        for program in lender["programs"]:
            tier = tier_mapping.get(program["tier"], program["tier_name"].lower().replace(" ", "_"))
            min_fico = program["min_fico"]
            max_fico = program["max_fico"]
            max_ltv = program["max_ltv"]
            days_basis = program.get("days_basis", "30/360")
            stips = json.dumps(program.get("stips_required", []))

            for rate_info in program["rates"]:
                term = rate_info["term"]
                apr = rate_info["apr"]
                dealer_cap = rate_info.get("dealer_reserve_cap", 2.0)

                rule_id = f"{lender_id}-{tier.upper()[:2]}-{term}"

                cursor.execute("""
                    INSERT OR REPLACE INTO lender_rules (
                        rule_id, lender_name, program_name, credit_tier,
                        min_fico, max_fico, min_term_months, max_term_months,
                        base_apr, max_ltv, min_loan_amount, max_loan_amount,
                        doc_fee, acquisition_fee, is_demo, effective_date,
                        expiration_date, days_basis, dealer_reserve_cap, stips_required
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule_id,
                    lender_name,
                    program.get("tier_name", tier),
                    tier,
                    min_fico,
                    max_fico,
                    term - 12,  # min_term = term - 12
                    term,       # max_term = term
                    apr,
                    max_ltv,
                    5000,
                    100000,
                    85,  # Standard doc fee
                    0,
                    True,
                    effective_date,
                    None,
                    days_basis,
                    dealer_cap,
                    stips if stips != "[]" else None
                ))
                count += 1

    return count


def seed_database(
    vehicle_count: int = DEFAULT_INVENTORY_COUNT,
    include_demo_data: bool = True,
    demo_customer_count: int = DEFAULT_DEMO_CUSTOMER_COUNT,
    demo_deal_count: int = DEFAULT_DEMO_DEAL_COUNT,
    demo_log_count: int = DEFAULT_DEMO_LOG_COUNT
):
    """Initialize database and seed with synthetic data."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Read and execute schema
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r") as f:
            cursor.executescript(f.read())
        print(f"Schema applied from {SCHEMA_PATH}")

    # Run migrations for existing databases
    run_migrations(cursor)

    # Clear existing inventory and lender_rules
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM lender_rules")

    # Insert vehicles with T01 fields
    vehicles = generate_vehicles(max(1, vehicle_count))
    for v in vehicles:
        cursor.execute("""
            INSERT INTO inventory (
                vin, make, model, year, trim, body_style,
                exterior_color, interior_color, mileage, price, msrp,
                fuel_type, transmission, drivetrain, engine, status, description,
                sb766_offering_price, add_ons, store_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v["vin"], v["make"], v["model"], v["year"], v["trim"], v["body_style"],
            v["exterior_color"], v["interior_color"], v["mileage"], v["price"], v["msrp"],
            v["fuel_type"], v["transmission"], v["drivetrain"], v["engine"], v["status"],
            v["description"], v["sb766_offering_price"], v["add_ons"], v["store_id"]
        ))
    print(f"Inserted {len(vehicles)} synthetic vehicles")

    # Insert base lender rules
    rules = generate_lender_rules()
    for r in rules:
        cursor.execute("""
            INSERT INTO lender_rules (
                rule_id, lender_name, program_name, credit_tier,
                min_fico, max_fico, min_term_months, max_term_months,
                base_apr, max_ltv, min_loan_amount, max_loan_amount,
                doc_fee, acquisition_fee, is_demo, effective_date, expiration_date,
                days_basis, dealer_reserve_cap, stips_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["rule_id"], r["lender_name"], r["program_name"], r["credit_tier"],
            r["min_fico"], r["max_fico"], r["min_term_months"], r["max_term_months"],
            r["base_apr"], r["max_ltv"], r["min_loan_amount"], r["max_loan_amount"],
            r["doc_fee"], r["acquisition_fee"], r["is_demo"], r["effective_date"],
            r["expiration_date"], r["days_basis"], r["dealer_reserve_cap"],
            r["stips_required"]
        ))
    print(f"Inserted {len(rules)} synthetic lender rules (Demo Capital)")

    # T01: Load reference data
    print("\n--- Loading T01 Reference Data ---")

    tax_count = load_tax_rates(cursor)
    print(f"Loaded {tax_count} tax jurisdictions")

    codes_count = load_adverse_action_codes(cursor)
    print(f"Loaded {codes_count} adverse action codes")

    programs_count = load_lender_programs(cursor)
    print(f"Loaded {programs_count} lender programs from reference data")

    demo_summary = None
    if include_demo_data:
        try:
            from scripts.generate_demo_data import seed_demo_data
        except ImportError:
            # Fallback for direct script execution from the scripts directory.
            from generate_demo_data import seed_demo_data

        print("\n--- Loading T06 Demo Data ---")
        demo_summary = seed_demo_data(
            conn=conn,
            compliance_log_count=max(0, demo_log_count),
            customer_count=max(0, demo_customer_count),
            deal_count=max(0, demo_deal_count),
            reset_existing=True
        )

    conn.commit()
    conn.close()

    print(f"\nDatabase seeded at: {DB_PATH}")
    print("\n⚠️  DEMO ONLY: All data is synthetic for demonstration purposes.")

    # Print summary
    print("\n--- T01 Data Foundation Summary ---")
    print(f"  Vehicles: {len(vehicles)} (with sb766_offering_price)")
    print(f"  Lender Rules: {len(rules) + programs_count}")
    print(f"  Tax Jurisdictions: {tax_count}")
    print(f"  Adverse Action Codes: {codes_count}")

    if demo_summary:
        print("\n--- T06 Demo Data Summary ---")
        print(f"  Compliance Logs: {demo_summary['compliance_logs']}")
        print(f"  Customers: {demo_summary['customers']}")
        print(f"  Deals: {demo_summary['deals']}")


def _parse_args():
    parser = argparse.ArgumentParser(description="Seed Mini-Lakebed demo database.")
    parser.add_argument(
        "--vehicles",
        type=int,
        default=DEFAULT_INVENTORY_COUNT,
        help=f"Number of synthetic vehicles to seed (default: {DEFAULT_INVENTORY_COUNT})"
    )
    parser.add_argument(
        "--skip-demo-data",
        action="store_true",
        help="Only seed T01 base data (inventory, rules, reference tables)."
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=DEFAULT_DEMO_CUSTOMER_COUNT,
        help=f"Number of demo customers to generate (default: {DEFAULT_DEMO_CUSTOMER_COUNT})"
    )
    parser.add_argument(
        "--deals",
        type=int,
        default=DEFAULT_DEMO_DEAL_COUNT,
        help=f"Number of demo deals to generate (default: {DEFAULT_DEMO_DEAL_COUNT})"
    )
    parser.add_argument(
        "--compliance-logs",
        type=int,
        default=DEFAULT_DEMO_LOG_COUNT,
        help=f"Number of compliance logs to generate (default: {DEFAULT_DEMO_LOG_COUNT})"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    seed_database(
        vehicle_count=args.vehicles,
        include_demo_data=not args.skip_demo_data,
        demo_customer_count=args.customers,
        demo_deal_count=args.deals,
        demo_log_count=args.compliance_logs
    )
