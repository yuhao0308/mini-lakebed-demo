"""
T02: Compliance Sentinel Unit Tests

Tests for SB 766 / CARS Act compliance enforcement.
Per tasks/T02_core_compliance.md
"""

import pytest
import asyncio
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.compliance_sentinel import ComplianceSentinel, build_offering_price
from app.services.disclosure_tracker import (
    DisclosureTracker, record_offering_price, check_offering_price_disclosed, clear_disclosures
)
from app.services.session_context import clear_session, record_disclosure, has_disclosure
from app.models.schemas import AddOn, OfferingPriceComponents


@pytest.fixture
def clean_session_id():
    """Provide a clean session ID for each test."""
    return "test_session_compliance"


@pytest.fixture
def sample_vehicle():
    """Sample vehicle for testing."""
    return {
        "id": 1,
        "make": "Toyota",
        "model": "Camry",
        "year": 2024,
        "price": 24000.00,
        "fuel_type": "gasoline",
        "sb766_offering_price": 24085.00,
        "add_ons": None
    }


# ============================================================================
# T02-01: test_payment_blocked_without_offering_price
# ============================================================================

@pytest.mark.asyncio
async def test_payment_blocked_without_offering_price(clean_session_id):
    """T02-01: Payment request without prior disclosure returns allowed=False."""
    session_id = clean_session_id
    vehicle_id = 1

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    sentinel = ComplianceSentinel()
    result = await sentinel.check_payment_allowed(session_id, vehicle_id)

    assert result.allowed is False
    assert result.violation is not None
    assert result.violation.code == "SB766_OFFERING_PRICE_REQUIRED"
    assert result.required_action == "SHOW_OFFERING_PRICE"

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)


# ============================================================================
# T02-02: test_payment_allowed_after_offering_price
# ============================================================================

@pytest.mark.asyncio
async def test_payment_allowed_after_offering_price(clean_session_id):
    """T02-02: Payment request after disclosure returns allowed=True."""
    session_id = clean_session_id
    vehicle_id = 1

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    # Record offering price disclosure
    components = OfferingPriceComponents(
        base_vehicle_price=24000.00,
        doc_fee=85.00,
        mandatory_addons=[],
        total_offering_price=24085.00
    )
    await record_offering_price(session_id, vehicle_id, 24085.00, components)

    sentinel = ComplianceSentinel()
    result = await sentinel.check_payment_allowed(session_id, vehicle_id)

    assert result.allowed is True
    assert result.violation is None

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)


# ============================================================================
# T02-03: test_offering_price_includes_doc_fee
# ============================================================================

@pytest.mark.asyncio
async def test_offering_price_includes_doc_fee():
    """T02-03: Offering price = base + doc_fee + mandatory_addons."""
    vehicle = {
        "id": 1,
        "price": 24000.00,
        "sb766_offering_price": 24085.00,
        "add_ons": None
    }

    offering = await build_offering_price(vehicle)

    # Verify components
    assert offering.base_vehicle_price == 24000.00
    assert offering.doc_fee == 85.00
    assert offering.total_offering_price == 24085.00


# ============================================================================
# T02-04: test_offering_price_excludes_taxes
# ============================================================================

@pytest.mark.asyncio
async def test_offering_price_excludes_taxes():
    """T02-04: Offering price does NOT include sales tax."""
    vehicle = {
        "id": 1,
        "price": 24000.00,
        "sb766_offering_price": 24085.00,
        "add_ons": None
    }

    offering = await build_offering_price(vehicle)

    # Offering price should be base + doc_fee (no tax component)
    # Tax would add ~7.75% = ~$1,866 for CA
    # Total should NOT include this
    expected_without_tax = 24000.00 + 85.00
    assert offering.total_offering_price == 24085.00
    # Verify no hidden tax (should be close to expected)
    assert abs(offering.total_offering_price - expected_without_tax) < 100


# ============================================================================
# T02-05: test_addon_blocked_no_benefit_statement
# ============================================================================

@pytest.mark.asyncio
async def test_addon_blocked_no_benefit_statement():
    """T02-05: AddOn with benefit_statement=None returns valid=False."""
    vehicle = {"id": 1, "fuel_type": "gasoline", "add_ons": None}

    addon = AddOn(
        add_on_id="ao_001",
        name="Theft Etch",
        price=299.00,
        benefit_statement=None,
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "no documented benefit" in result.reason.lower()
    assert result.regulation == "CARS Act - Valueless Add-on"


# ============================================================================
# T02-06: test_addon_blocked_ev_oil_change
# ============================================================================

@pytest.mark.asyncio
async def test_addon_blocked_ev_oil_change():
    """T02-06: Oil change addon on electric vehicle returns valid=False."""
    vehicle = {"id": 1, "fuel_type": "electric", "add_ons": None}

    addon = AddOn(
        add_on_id="ao_002",
        name="Oil Change Package",
        price=199.00,
        benefit_statement="Regular oil changes protect your engine",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "electric" in result.reason.lower() or "oil" in result.reason.lower()
    assert result.regulation == "CARS Act - Valueless Add-on"


# ============================================================================
# T02-07: test_addon_allowed_valid_benefit
# ============================================================================

@pytest.mark.asyncio
async def test_addon_allowed_valid_benefit():
    """T02-07: AddOn with valid benefit statement returns valid=True."""
    vehicle = {"id": 1, "fuel_type": "gasoline", "add_ons": None}

    addon = AddOn(
        add_on_id="ao_003",
        name="Nitrogen Tire Fill",
        price=149.00,
        benefit_statement="Maintains tire pressure longer for better fuel economy",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is True
    assert result.reason is None


# ============================================================================
# T02-08: test_compliance_violation_logged
# ============================================================================

@pytest.mark.asyncio
async def test_compliance_violation_logged(clean_session_id):
    """T02-08: Violation creates audit log entry with payload_hash."""
    session_id = clean_session_id + "_violation_log"
    vehicle_id = 99

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    sentinel = ComplianceSentinel()

    # This should create a violation and log it
    result = await sentinel.check_payment_allowed(session_id, vehicle_id)

    assert result.allowed is False

    # Check audit log was created
    from app.services.database import execute_query

    logs = await execute_query(
        """
        SELECT * FROM audit_logs
        WHERE session_id = ? AND event_type = 'payment_blocked_no_disclosure'
        ORDER BY timestamp DESC LIMIT 1
        """,
        (session_id,)
    )

    assert len(logs) >= 1
    log = logs[0]
    assert log["actor"] == "agent:compliance"
    assert log["payload_hash"] is not None
    assert len(log["payload_hash"]) == 64  # SHA-256 hex

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)
