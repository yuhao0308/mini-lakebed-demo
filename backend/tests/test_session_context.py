"""
Unit tests for Session Context Service.

Tests all session state fields:
- current_vehicle
- recent_vehicles  
- last_payment
- chat_history
- awaiting_input
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime

# Add parent to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.session_context import (
    SessionContext,
    get_session,
    update_current_vehicle,
    update_recent_vehicles,
    get_current_vehicle,
    resolve_vehicle_reference,
    update_last_payment,
    get_last_payment,
    add_chat_message,
    get_chat_history,
    update_awaiting_input,
    get_awaiting_input,
    clear_awaiting_input,
    clear_session,
)


# Fixtures
@pytest.fixture
def sample_vehicle():
    return {
        "id": 1,
        "make": "Toyota",
        "model": "Camry",
        "year": 2024,
        "price": 28500,
        "body_style": "sedan"
    }


@pytest.fixture
def sample_vehicles():
    return [
        {"id": i, "make": "Test", "model": f"Model{i}", "year": 2024, "price": 20000 + i*1000}
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_payment():
    return {
        "vehicle_price": 28500,
        "down_payment": 5000,
        "monthly_payment": 450.00,
        "apr": 5.9,
        "term_months": 60
    }


@pytest_asyncio.fixture
async def clean_session():
    """Provide a clean session for each test."""
    session_id = f"test-session-{datetime.now().timestamp()}"
    yield session_id
    await clear_session(session_id)


# ============================================================
# SessionContext Class Tests
# ============================================================

class TestSessionContextClass:
    """Test the SessionContext dataclass methods."""
    
    def test_initialization(self):
        """Test SessionContext initializes with correct defaults."""
        session = SessionContext(session_id="test-123")
        
        assert session.session_id == "test-123"
        assert session.current_vehicle is None
        assert session.recent_vehicles == []
        assert session.last_payment is None
        assert session.chat_history == []
        assert session.awaiting_input is None
    
    def test_set_current_vehicle(self, sample_vehicle):
        """Test setting current vehicle updates state and timestamp."""
        session = SessionContext(session_id="test")
        initial_time = session.last_activity
        
        session.set_current_vehicle(sample_vehicle)
        
        assert session.current_vehicle == sample_vehicle
        assert session.last_activity >= initial_time
    
    def test_set_recent_vehicles_limits_to_10(self, sample_vehicles):
        """Test recent_vehicles is limited to 10 items."""
        session = SessionContext(session_id="test")
        
        # Create 15 vehicles
        many_vehicles = [{"id": i} for i in range(15)]
        session.set_recent_vehicles(many_vehicles)
        
        assert len(session.recent_vehicles) == 10
        assert session.recent_vehicles[0]["id"] == 0
        assert session.recent_vehicles[9]["id"] == 9
    
    def test_set_last_payment(self, sample_payment):
        """Test setting last payment."""
        session = SessionContext(session_id="test")
        session.set_last_payment(sample_payment)
        
        assert session.last_payment == sample_payment
    
    def test_set_awaiting_input(self):
        """Test setting awaiting_input state."""
        session = SessionContext(session_id="test")
        
        session.set_awaiting_input("payment_info")
        assert session.awaiting_input == "payment_info"
        
        session.set_awaiting_input(None)
        assert session.awaiting_input is None
    
    def test_add_chat_turn_stores_messages(self):
        """Test chat history stores messages correctly."""
        session = SessionContext(session_id="test")
        
        session.add_chat_turn("user", "Hello")
        session.add_chat_turn("assistant", "Hi there!")
        
        assert len(session.chat_history) == 2
        assert session.chat_history[0]["role"] == "user"
        assert session.chat_history[0]["content"] == "Hello"
        assert session.chat_history[1]["role"] == "assistant"
    
    def test_add_chat_turn_trims_history(self):
        """Test chat history is trimmed to max turns."""
        session = SessionContext(session_id="test")
        
        # Add 25 messages (12.5 turns)
        for i in range(25):
            role = "user" if i % 2 == 0 else "assistant"
            session.add_chat_turn(role, f"Message {i}", max_turns=5)
        
        # Should keep only last 10 messages (5 turns * 2)
        assert len(session.chat_history) == 10
        assert session.chat_history[0]["content"] == "Message 15"


# ============================================================
# Vehicle Reference Resolution Tests
# ============================================================

class TestVehicleReferenceResolution:
    """Test pronoun and numbered reference resolution."""
    
    def test_resolve_numbered_reference(self, sample_vehicles):
        """Test '#3' resolves to third vehicle."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)
        
        result = session.get_vehicle_by_reference("#3")
        
        assert result is not None
        assert result["id"] == 3
    
    def test_resolve_ordinal_first(self, sample_vehicles):
        """Test 'the first one' resolves correctly."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)
        
        result = session.get_vehicle_by_reference("the first one")
        
        assert result is not None
        assert result["id"] == 1
    
    def test_resolve_ordinal_last(self, sample_vehicles):
        """Test 'the last one' resolves correctly."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)
        
        result = session.get_vehicle_by_reference("the last one")
        
        assert result is not None
        assert result["id"] == 5
    
    def test_resolve_that_one_uses_current_vehicle(self, sample_vehicle):
        """Test 'that one' returns current_vehicle."""
        session = SessionContext(session_id="test")
        session.set_current_vehicle(sample_vehicle)
        
        result = session.get_vehicle_by_reference("that one")
        
        assert result == sample_vehicle
    
    def test_resolve_invalid_reference_returns_none(self):
        """Test invalid reference returns None."""
        session = SessionContext(session_id="test")
        
        result = session.get_vehicle_by_reference("the purple one")
        
        assert result is None
    
    def test_resolve_out_of_range_returns_none(self, sample_vehicles):
        """Test out-of-range number returns None."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)  # Only 5 vehicles
        
        result = session.get_vehicle_by_reference("#10")
        
        assert result is None
    
    def test_resolve_plain_number(self, sample_vehicles):
        """Test '3' (plain number) resolves to third vehicle."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)
        
        result = session.get_vehicle_by_reference("3")
        
        assert result is not None
        assert result["id"] == 3
    
    def test_resolve_about_number(self, sample_vehicles):
        """Test 'about 3' resolves to third vehicle."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)
        
        result = session.get_vehicle_by_reference("about 3")
        
        assert result is not None
        assert result["id"] == 3
    
    def test_resolve_vehicle_number(self, sample_vehicles):
        """Test 'vehicle 2' resolves to second vehicle."""
        session = SessionContext(session_id="test")
        session.set_recent_vehicles(sample_vehicles)
        
        result = session.get_vehicle_by_reference("vehicle 2")
        
        assert result is not None
        assert result["id"] == 2


# ============================================================
# Async Helper Function Tests
# ============================================================

class TestAsyncHelpers:
    """Test the module-level async helper functions."""
    
    @pytest.mark.asyncio
    async def test_get_session_creates_new(self, clean_session):
        """Test get_session creates new session if not exists."""
        session = await get_session(clean_session)
        
        assert session is not None
        assert session.session_id == clean_session
    
    @pytest.mark.asyncio
    async def test_get_session_returns_same(self, clean_session):
        """Test get_session returns same session on subsequent calls."""
        session1 = await get_session(clean_session)
        session1.current_vehicle = {"id": 999}
        
        session2 = await get_session(clean_session)
        
        assert session2.current_vehicle["id"] == 999
    
    @pytest.mark.asyncio
    async def test_update_and_get_current_vehicle(self, clean_session, sample_vehicle):
        """Test update/get current vehicle flow."""
        await update_current_vehicle(clean_session, sample_vehicle)
        result = await get_current_vehicle(clean_session)
        
        assert result == sample_vehicle
    
    @pytest.mark.asyncio
    async def test_update_and_get_recent_vehicles(self, clean_session, sample_vehicles):
        """Test update/get recent vehicles flow."""
        await update_recent_vehicles(clean_session, sample_vehicles)
        result = await resolve_vehicle_reference(clean_session, "#2")
        
        assert result["id"] == 2
    
    @pytest.mark.asyncio
    async def test_update_and_get_last_payment(self, clean_session, sample_payment):
        """Test update/get last payment flow."""
        await update_last_payment(clean_session, sample_payment)
        result = await get_last_payment(clean_session)
        
        assert result == sample_payment
    
    @pytest.mark.asyncio
    async def test_awaiting_input_lifecycle(self, clean_session):
        """Test awaiting_input set/get/clear flow."""
        # Initially none
        assert await get_awaiting_input(clean_session) is None
        
        # Set waiting
        await update_awaiting_input(clean_session, "payment_info")
        assert await get_awaiting_input(clean_session) == "payment_info"
        
        # Clear
        await clear_awaiting_input(clean_session)
        assert await get_awaiting_input(clean_session) is None
    
    @pytest.mark.asyncio
    async def test_chat_history_lifecycle(self, clean_session):
        """Test chat history add/get flow."""
        await add_chat_message(clean_session, "user", "Hello")
        await add_chat_message(clean_session, "assistant", "Hi!")
        
        history = await get_chat_history(clean_session, max_turns=5)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["content"] == "Hi!"


# ============================================================
# Integration Scenario Tests
# ============================================================

class TestIntegrationScenarios:
    """Test realistic conversation flows."""
    
    @pytest.mark.asyncio
    async def test_search_then_select_flow(self, clean_session, sample_vehicles):
        """User searches, then asks about #3."""
        # 1. Search returns results
        await update_recent_vehicles(clean_session, sample_vehicles)
        
        # 2. User asks "tell me about #3"
        vehicle = await resolve_vehicle_reference(clean_session, "#3")
        assert vehicle is not None
        
        # 3. Update current vehicle
        await update_current_vehicle(clean_session, vehicle)
        
        # 4. Current vehicle should be #3
        current = await get_current_vehicle(clean_session)
        assert current["id"] == 3
    
    @pytest.mark.asyncio
    async def test_payment_missing_info_flow(self, clean_session, sample_vehicle):
        """User asks for payment but missing credit info."""
        # 1. User viewing a vehicle
        await update_current_vehicle(clean_session, sample_vehicle)
        
        # 2. User asks for payment, missing info
        await update_awaiting_input(clean_session, "payment_info")
        assert await get_awaiting_input(clean_session) == "payment_info"
        
        # 3. User provides info
        await clear_awaiting_input(clean_session)
        assert await get_awaiting_input(clean_session) is None
        
        # 4. Payment calculated, saved
        payment = {"monthly": 450}
        await update_last_payment(clean_session, payment)
        assert await get_last_payment(clean_session) == payment
    
    @pytest.mark.asyncio  
    async def test_full_conversation_flow(self, clean_session, sample_vehicles, sample_payment):
        """Full realistic conversation flow."""
        # Chat messages
        await add_chat_message(clean_session, "user", "Show me SUVs under 40k")
        await add_chat_message(clean_session, "assistant", "Found 5 vehicles...")
        
        # Search results
        await update_recent_vehicles(clean_session, sample_vehicles)
        
        # User selects
        await add_chat_message(clean_session, "user", "Tell me about the first one")
        vehicle = await resolve_vehicle_reference(clean_session, "the first one")
        await update_current_vehicle(clean_session, vehicle)
        
        # User asks payment
        await add_chat_message(clean_session, "user", "What's the payment?")
        await update_awaiting_input(clean_session, "payment_info")
        
        # User provides info
        await add_chat_message(clean_session, "user", "I have good credit, 5k down")
        await clear_awaiting_input(clean_session)
        await update_last_payment(clean_session, sample_payment)
        
        # Verify final state
        session = await get_session(clean_session)
        assert session.current_vehicle["id"] == 1
        assert session.last_payment == sample_payment
        assert session.awaiting_input is None
        assert len(session.chat_history) == 5
