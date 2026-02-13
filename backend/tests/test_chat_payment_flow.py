"""
Tests for chat payment flow behavior.

These tests verify:
1. "first car" resolution after search results
2. Multi-turn payment flow (vehicle -> credit/down prompt -> user provides -> payment)
3. One-shot payment query with vehicle + credit + down in single message
4. Entity extraction for payment queries
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm import (
    _extract_payment_entities,
    _extract_vehicle_reference,
    _fallback_classification,
    Intent,
    ExtractedEntities
)
from app.services.session_context import (
    SessionContext,
    get_session,
    update_recent_vehicles,
    resolve_vehicle_reference,
    clear_session
)


class TestPaymentEntityExtraction:
    """Tests for payment entity extraction including vehicle references."""

    def test_extract_down_payment_with_dollar_sign(self):
        """Test extracting '$5,000 down'."""
        entities = _extract_payment_entities("I have $5,000 down")
        assert entities.down_payment == 5000.0

    def test_extract_down_payment_with_k_suffix(self):
        """Test extracting '$5k down'."""
        entities = _extract_payment_entities("I have $5k down")
        assert entities.down_payment == 5000.0

    def test_extract_credit_tier_good(self):
        """Test extracting 'good credit'."""
        entities = _extract_payment_entities("I have good credit")
        assert entities.credit_tier == "prime"

    def test_extract_credit_tier_excellent(self):
        """Test extracting 'excellent credit'."""
        entities = _extract_payment_entities("I have excellent credit")
        assert entities.credit_tier == "super_prime"

    def test_extract_fico_score(self):
        """Test extracting numeric FICO score."""
        entities = _extract_payment_entities("My credit score is 720")
        assert entities.fico_estimate == 720

    def test_extract_combined_credit_and_down(self):
        """Test extracting both credit and down payment from one message."""
        entities = _extract_payment_entities("I have good credit and $5,000 down")
        assert entities.credit_tier == "prime"
        assert entities.down_payment == 5000.0

    def test_extract_vehicle_reference_first_car(self):
        """Test that 'first car' is extracted as vehicle reference."""
        entities = _extract_payment_entities("What's the monthly payment on the first car?")
        assert entities.vehicle_reference == "the first one"

    def test_extract_vehicle_reference_number(self):
        """Test that '#3' is extracted as vehicle reference."""
        entities = _extract_payment_entities("What's the payment on #3?")
        assert entities.vehicle_reference == "#3"

    def test_extract_make_model_year(self):
        """Test extracting make/model/year from payment query."""
        entities = _extract_payment_entities(
            "What's the monthly payment on the 2020 Ford Bronco?"
        )
        assert entities.make == "Ford"
        assert entities.min_year == 2020

    def test_full_payment_query_extraction(self):
        """Test extracting all entities from a complete payment query."""
        msg = "What's the monthly payment on the 2020 Ford? I have good credit and $5,000 down"
        entities = _extract_payment_entities(msg)
        assert entities.make == "Ford"
        assert entities.min_year == 2020
        assert entities.credit_tier == "prime"
        assert entities.down_payment == 5000.0


class TestVehicleReferenceExtraction:
    """Tests for vehicle reference extraction patterns."""

    def test_extract_first(self):
        """Test 'first' ordinal."""
        ref = _extract_vehicle_reference("the first car")
        assert ref == "the first one"

    def test_extract_second(self):
        """Test 'second' ordinal."""
        ref = _extract_vehicle_reference("tell me about the second one")
        assert ref == "the second one"

    def test_extract_hash_number(self):
        """Test '#3' pattern."""
        ref = _extract_vehicle_reference("show me #3")
        assert ref == "#3"

    def test_extract_number_only(self):
        """Test standalone number."""
        ref = _extract_vehicle_reference("3")
        assert ref == "#3"

    def test_extract_ordinal_suffix(self):
        """Test '3rd' pattern."""
        ref = _extract_vehicle_reference("the 3rd vehicle")
        assert ref == "#3"

    def test_extract_that_one(self):
        """Test 'that one' pronoun."""
        ref = _extract_vehicle_reference("tell me about that one")
        assert ref == "that one"

    def test_no_reference(self):
        """Test message without vehicle reference."""
        ref = _extract_vehicle_reference("show me SUVs under $30,000")
        assert ref is None


class TestFallbackClassification:
    """Tests for fallback intent classification."""

    def test_payment_with_credit_returns_payment_estimate(self):
        """Payment query with credit info should return PAYMENT_ESTIMATE."""
        result = _fallback_classification(
            "What's the monthly payment? I have good credit and $5,000 down"
        )
        assert result.intent == Intent.PAYMENT_ESTIMATE
        assert result.entities.credit_tier == "prime"
        assert result.entities.down_payment == 5000.0

    def test_payment_without_credit_returns_payment_inquiry(self):
        """Payment query without credit info should return PAYMENT_INQUIRY."""
        result = _fallback_classification("What's the monthly payment on this car?")
        assert result.intent == Intent.PAYMENT_INQUIRY

    def test_payment_with_vehicle_reference(self):
        """Payment query with vehicle reference should extract it."""
        result = _fallback_classification("What's the payment on the first car?")
        assert result.intent == Intent.PAYMENT_INQUIRY
        assert result.entities.vehicle_reference == "the first one"

    def test_credit_prequalification(self):
        """Pre-approval question should return CREDIT_PREQUALIFICATION."""
        result = _fallback_classification("Can I get pre-approved?")
        assert result.intent == Intent.CREDIT_PREQUALIFICATION


class TestSessionVehicleResolution:
    """Tests for resolving vehicle references from session context."""

    @pytest.fixture
    def sample_vehicles(self):
        """Sample search results."""
        return [
            {"id": 1, "year": 2020, "make": "Ford", "model": "Bronco Sport", "price": 28000},
            {"id": 2, "year": 2021, "make": "Toyota", "model": "RAV4", "price": 32000},
            {"id": 3, "year": 2019, "make": "Honda", "model": "CR-V", "price": 26000},
        ]

    @pytest.mark.asyncio
    async def test_resolve_first_car(self, sample_vehicles):
        """Test resolving 'first car' to first search result."""
        session_id = "test_first_car"
        await clear_session(session_id)

        # Simulate search results being stored
        await update_recent_vehicles(session_id, sample_vehicles)

        # Resolve "the first one"
        vehicle = await resolve_vehicle_reference(session_id, "the first one")
        assert vehicle is not None
        assert vehicle["id"] == 1
        assert vehicle["make"] == "Ford"

        await clear_session(session_id)

    @pytest.mark.asyncio
    async def test_resolve_hash_3(self, sample_vehicles):
        """Test resolving '#3' to third search result."""
        session_id = "test_hash_3"
        await clear_session(session_id)

        await update_recent_vehicles(session_id, sample_vehicles)

        vehicle = await resolve_vehicle_reference(session_id, "#3")
        assert vehicle is not None
        assert vehicle["id"] == 3
        assert vehicle["make"] == "Honda"

        await clear_session(session_id)

    @pytest.mark.asyncio
    async def test_resolve_last(self, sample_vehicles):
        """Test resolving 'last' to last search result."""
        session_id = "test_last"
        await clear_session(session_id)

        await update_recent_vehicles(session_id, sample_vehicles)

        vehicle = await resolve_vehicle_reference(session_id, "the last one")
        assert vehicle is not None
        assert vehicle["id"] == 3

        await clear_session(session_id)

    @pytest.mark.asyncio
    async def test_resolve_out_of_range(self, sample_vehicles):
        """Test resolving '#10' when only 3 results exist."""
        session_id = "test_out_of_range"
        await clear_session(session_id)

        await update_recent_vehicles(session_id, sample_vehicles)

        vehicle = await resolve_vehicle_reference(session_id, "#10")
        assert vehicle is None

        await clear_session(session_id)


class TestMultiTurnPaymentFlow:
    """Integration tests for multi-turn payment conversations."""

    @pytest.mark.asyncio
    async def test_payment_info_state_stored(self):
        """Test that payment_info awaiting state is properly stored."""
        from app.services.session_context import (
            update_awaiting_input, get_awaiting_input, clear_session
        )

        session_id = "test_payment_state"
        await clear_session(session_id)

        # Simulate setting payment_info state
        await update_awaiting_input(session_id, "payment_info")
        state = await get_awaiting_input(session_id)
        assert state == "payment_info"

        await clear_session(session_id)

    @pytest.mark.asyncio
    async def test_session_context_get_vehicle_by_reference(self):
        """Test SessionContext.get_vehicle_by_reference method."""
        context = SessionContext(session_id="test_context")
        context.recent_vehicles = [
            {"id": 1, "make": "Ford"},
            {"id": 2, "make": "Toyota"},
            {"id": 3, "make": "Honda"},
        ]

        # Test "first"
        vehicle = context.get_vehicle_by_reference("the first one")
        assert vehicle["id"] == 1

        # Test "#2"
        vehicle = context.get_vehicle_by_reference("#2")
        assert vehicle["id"] == 2

        # Test "third"
        vehicle = context.get_vehicle_by_reference("the third")
        assert vehicle["id"] == 3

        # Test current vehicle with "that one"
        context.current_vehicle = {"id": 99, "make": "BMW"}
        vehicle = context.get_vehicle_by_reference("that one")
        assert vehicle["id"] == 99
