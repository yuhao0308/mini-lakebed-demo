"""
T02: SB 766 Disclosure Integration Tests

Tests for the disclosure flow in the chat interface.
Per tasks/T02_core_compliance.md
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import ChatRequest, ChatResponse, OfferingPriceComponents
from app.services.session_context import (
    clear_session, update_current_vehicle, get_session,
    record_disclosure, has_disclosure
)
from app.services.disclosure_tracker import clear_disclosures, record_offering_price
from app.services.llm import Intent


@pytest.fixture
def clean_session_id():
    """Provide a clean session ID for each test."""
    return "test_session_sb766"


@pytest.fixture
def sample_vehicle():
    """Sample vehicle for testing."""
    return {
        "id": 1,
        "make": "Toyota",
        "model": "Camry",
        "year": 2024,
        "trim": "LE",
        "price": 24000.00,
        "mileage": 0,
        "body_style": "sedan",
        "status": "available",
        "exterior_color": "Silver",
        "interior_color": "Black",
        "fuel_type": "gasoline",
        "transmission": "automatic",
        "drivetrain": "FWD",
        "engine": "2.5L 4-Cyl",
        "sb766_offering_price": 24085.00,
        "add_ons": None
    }


# ============================================================================
# T02-09: test_chat_payment_triggers_disclosure
# ============================================================================

@pytest.mark.asyncio
async def test_chat_payment_triggers_disclosure(clean_session_id, sample_vehicle):
    """T02-09: 'What's the monthly payment?' returns offering price first."""
    session_id = clean_session_id + "_triggers"

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    # Set up vehicle in session context
    await update_current_vehicle(session_id, sample_vehicle)

    # Import chat handler
    from app.routers.chat import _handle_payment_inquiry

    # Handle payment inquiry
    response, tool_calls = await _handle_payment_inquiry(
        entities=type('obj', (object,), {})(),  # Empty entities
        tool_calls=[],
        session_id=session_id
    )

    # Should return offering price disclosure
    assert "Offering Price" in response
    assert "$24,085" in response or "24,085" in response
    assert "Toyota" in response or "Camry" in response

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)


# ============================================================================
# T02-10: test_chat_after_disclosure_returns_payment
# ============================================================================

@pytest.mark.asyncio
async def test_chat_after_disclosure_returns_payment(clean_session_id, sample_vehicle):
    """T02-10: Second payment request (after disclosure) returns payment."""
    session_id = clean_session_id + "_after"
    vehicle_id = sample_vehicle["id"]

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    # Set up vehicle in session context
    await update_current_vehicle(session_id, sample_vehicle)

    # Record that offering price was already disclosed
    components = OfferingPriceComponents(
        base_vehicle_price=24000.00,
        doc_fee=85.00,
        mandatory_addons=[],
        total_offering_price=24085.00
    )
    await record_disclosure(session_id, vehicle_id, "offering_price", {
        "total": 24085.00
    })
    await record_offering_price(session_id, vehicle_id, 24085.00, components)

    # Now request payment inquiry again
    from app.routers.chat import _handle_payment_inquiry

    response, tool_calls = await _handle_payment_inquiry(
        entities=type('obj', (object,), {})(),
        tool_calls=[],
        session_id=session_id
    )

    # Should prompt for payment details (not offering price again)
    assert "credit" in response.lower() or "down payment" in response.lower()
    # Should NOT show offering price again
    assert "Before we get to payments" not in response

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)


# ============================================================================
# T02-11: test_disclosure_per_vehicle
# ============================================================================

@pytest.mark.asyncio
async def test_disclosure_per_vehicle(clean_session_id, sample_vehicle):
    """T02-11: Disclosure for vehicle A does not satisfy vehicle B."""
    session_id = clean_session_id + "_per_vehicle"

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    vehicle_a = {**sample_vehicle, "id": 1}
    vehicle_b = {**sample_vehicle, "id": 2, "make": "Honda", "model": "Accord"}

    # Disclose offering price for vehicle A
    components = OfferingPriceComponents(
        base_vehicle_price=24000.00,
        doc_fee=85.00,
        mandatory_addons=[],
        total_offering_price=24085.00
    )
    await record_disclosure(session_id, vehicle_a["id"], "offering_price", {"total": 24085.00})
    await record_offering_price(session_id, vehicle_a["id"], 24085.00, components)

    # Check: Vehicle A should have disclosure
    has_a = await has_disclosure(session_id, vehicle_a["id"], "offering_price")
    assert has_a is True

    # Check: Vehicle B should NOT have disclosure
    has_b = await has_disclosure(session_id, vehicle_b["id"], "offering_price")
    assert has_b is False

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)


# ============================================================================
# T02-12: test_disclosure_persists_in_session
# ============================================================================

@pytest.mark.asyncio
async def test_disclosure_persists_in_session(clean_session_id, sample_vehicle):
    """T02-12: Disclosure valid for entire session."""
    session_id = clean_session_id + "_persists"
    vehicle_id = sample_vehicle["id"]

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    # Record disclosure
    components = OfferingPriceComponents(
        base_vehicle_price=24000.00,
        doc_fee=85.00,
        mandatory_addons=[],
        total_offering_price=24085.00
    )
    await record_disclosure(session_id, vehicle_id, "offering_price", {"total": 24085.00})
    await record_offering_price(session_id, vehicle_id, 24085.00, components)

    # Check multiple times - should persist
    for _ in range(3):
        has_disc = await has_disclosure(session_id, vehicle_id, "offering_price")
        assert has_disc is True

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)


# ============================================================================
# T02-13: test_disclosure_format_sb766_compliant
# ============================================================================

@pytest.mark.asyncio
async def test_disclosure_format_sb766_compliant(clean_session_id, sample_vehicle):
    """T02-13: Response includes itemized breakdown per SB 766 format."""
    session_id = clean_session_id + "_format"

    # Clean up before test
    await clear_session(session_id)
    await clear_disclosures(session_id)

    # Set up vehicle in session context
    await update_current_vehicle(session_id, sample_vehicle)

    from app.routers.chat import _handle_payment_inquiry

    response, _ = await _handle_payment_inquiry(
        entities=type('obj', (object,), {})(),
        tool_calls=[],
        session_id=session_id
    )

    # Check SB 766 required elements
    assert "Offering Price" in response
    assert "Base vehicle price" in response or "base" in response.lower()
    assert "doc" in response.lower() or "Documentation" in response
    assert "tax" in response.lower()  # Should mention taxes are extra
    assert "$" in response  # Should show dollar amounts

    # Clean up after test
    await clear_session(session_id)
    await clear_disclosures(session_id)
