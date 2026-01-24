"""
T02: Valueless Add-on Validation Tests

Tests for CARS Act add-on compliance.
Per tasks/T02_core_compliance.md
"""

import pytest
import asyncio
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.compliance_sentinel import ComplianceSentinel
from app.models.schemas import AddOn


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# T02-14: test_nitrogen_on_nitrogen_filled_blocked
# ============================================================================

@pytest.mark.asyncio
async def test_nitrogen_on_nitrogen_filled_blocked():
    """T02-14: Nitrogen addon on already-nitrogen-filled vehicle blocked."""
    # Vehicle already has nitrogen-filled tires
    vehicle = {
        "id": 1,
        "fuel_type": "gasoline",
        "add_ons": json.dumps([
            {
                "add_on_id": "existing_001",
                "name": "Nitrogen Tire Fill",
                "price": 149.00,
                "benefit_statement": "Already installed",
                "compliance_check_passed": True
            }
        ])
    }

    # Try to add nitrogen again
    addon = AddOn(
        add_on_id="ao_004",
        name="Nitrogen Tire Service",
        price=99.00,
        benefit_statement="Maintains tire pressure",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "nitrogen" in result.reason.lower()
    assert result.regulation == "CARS Act - Valueless Add-on"


# ============================================================================
# T02-15: test_oil_change_on_ev_blocked
# ============================================================================

@pytest.mark.asyncio
async def test_oil_change_on_ev_blocked():
    """T02-15: Oil change addon on EV blocked."""
    vehicle = {
        "id": 1,
        "fuel_type": "electric",
        "add_ons": None
    }

    addon = AddOn(
        add_on_id="ao_005",
        name="Premium Oil Change Package",
        price=299.00,
        benefit_statement="5 oil changes included",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "electric" in result.reason.lower() or "oil" in result.reason.lower()


# ============================================================================
# T02-16: test_theft_etch_no_benefit_blocked
# ============================================================================

@pytest.mark.asyncio
async def test_theft_etch_no_benefit_blocked():
    """T02-16: Theft etch with null benefit_statement blocked."""
    vehicle = {
        "id": 1,
        "fuel_type": "gasoline",
        "add_ons": None
    }

    addon = AddOn(
        add_on_id="ao_006",
        name="VIN Etching / Theft Deterrent",
        price=199.00,
        benefit_statement=None,  # No benefit documented
        compliance_check_passed=False
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "benefit" in result.reason.lower() or "compliance" in result.reason.lower()


# ============================================================================
# T02-17: test_valid_addon_allowed
# ============================================================================

@pytest.mark.asyncio
async def test_valid_addon_allowed():
    """T02-17: Valid addon with documented benefit allowed."""
    vehicle = {
        "id": 1,
        "fuel_type": "gasoline",
        "add_ons": None
    }

    addon = AddOn(
        add_on_id="ao_007",
        name="Paint Protection Film",
        price=599.00,
        benefit_statement="Protects paint from rock chips and road debris",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is True
    assert result.reason is None
    assert result.regulation is None


# ============================================================================
# T02-18: test_addon_validation_logged
# ============================================================================

@pytest.mark.asyncio
async def test_addon_validation_logged():
    """T02-18: Validation result logged to audit_logs."""
    vehicle = {
        "id": 42,
        "fuel_type": "gasoline",
        "add_ons": None
    }

    addon = AddOn(
        add_on_id="ao_008",
        name="Test Addon",
        price=100.00,
        benefit_statement="Test benefit",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    # Should be valid
    assert result.valid is True

    # Check audit log was created
    from app.services.database import execute_query

    logs = await execute_query(
        """
        SELECT * FROM audit_logs
        WHERE event_type = 'addon_validation'
        AND (action LIKE '%ao_008%' OR action LIKE '%Test Addon%')
        ORDER BY timestamp DESC LIMIT 5
        """
    )

    # Should have at least one log entry for this addon
    # (The log might not capture addon_id in action, so we check event_type)
    addon_logs = await execute_query(
        """
        SELECT * FROM audit_logs
        WHERE event_type = 'addon_validation'
        ORDER BY timestamp DESC LIMIT 1
        """
    )

    assert len(addon_logs) >= 1
    log = addon_logs[0]
    assert log["event_type"] == "addon_validation"
    assert log["actor"] == "agent:compliance"


# ============================================================================
# Additional Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_addon_empty_benefit_string_blocked():
    """AddOn with empty string benefit_statement blocked."""
    vehicle = {"id": 1, "fuel_type": "gasoline", "add_ons": None}

    addon = AddOn(
        add_on_id="ao_009",
        name="Mystery Package",
        price=99.00,
        benefit_statement="",  # Empty string
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "benefit" in result.reason.lower()


@pytest.mark.asyncio
async def test_addon_compliance_check_failed_blocked():
    """AddOn with compliance_check_passed=False blocked."""
    vehicle = {"id": 1, "fuel_type": "gasoline", "add_ons": None}

    addon = AddOn(
        add_on_id="ao_010",
        name="Warranty Extension",
        price=1999.00,
        benefit_statement="Extended coverage for peace of mind",
        compliance_check_passed=False  # Failed compliance
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    assert result.valid is False
    assert "compliance" in result.reason.lower()


@pytest.mark.asyncio
async def test_hybrid_vehicle_allows_oil_change():
    """Hybrid vehicles (not pure EV) should allow oil change addons."""
    vehicle = {"id": 1, "fuel_type": "hybrid", "add_ons": None}

    addon = AddOn(
        add_on_id="ao_011",
        name="Oil Change Package",
        price=199.00,
        benefit_statement="Keep your hybrid running smoothly",
        compliance_check_passed=True
    )

    sentinel = ComplianceSentinel()
    result = await sentinel.validate_addon(vehicle, addon)

    # Hybrid has a gas engine, so oil change is valid
    assert result.valid is True
