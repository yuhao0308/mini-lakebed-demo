"""
Session Context Service for conversation state management.

Tracks the conversation context including:
- Last viewed vehicle (for payment context)
- Session metadata

Uses in-memory storage for simplicity (suitable for demo).
Production would use Redis or database-backed sessions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio


@dataclass
class SessionContext:
    """Conversation context for a single session."""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # The currently "discussed" or last-viewed vehicle
    current_vehicle: Optional[Dict[str, Any]] = None

    # Last few vehicles shown in search results (for "the first one", "that one" resolution)
    recent_vehicles: list = field(default_factory=list)

    # Last payment calculation result (for "what if I put $10k down instead?")
    last_payment: Optional[Dict[str, Any]] = None

    # Chat history for context (last N turns)
    chat_history: list = field(default_factory=list)  # [{role, content}, ...]

    # Conversation state
    awaiting_input: Optional[str] = None  # e.g., "credit_info", "down_payment"

    # T02: Disclosures tracking per vehicle
    # Key: vehicle_id, Value: disclosure record with timestamp
    disclosures_shown: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # T03: Credit flow tracking
    credit_status: Optional[Dict[str, Any]] = None  # Credit tier, decision, etc.
    fcra_consent: Optional[Dict[str, Any]] = None  # Active FCRA consent record
    customer_id: Optional[str] = None  # Customer ID for credit operations

    def set_current_vehicle(self, vehicle: Dict[str, Any]):
        """Set the currently discussed vehicle."""
        self.current_vehicle = vehicle
        self.last_activity = datetime.now()
    
    def set_recent_vehicles(self, vehicles: list):
        """Set the recently shown vehicles from a search."""
        self.recent_vehicles = vehicles[:10]  # Keep last 10
        self.last_activity = datetime.now()
    
    def set_last_payment(self, payment: Dict[str, Any]):
        """Store the last payment calculation result."""
        self.last_payment = payment
        self.last_activity = datetime.now()
    
    def set_awaiting_input(self, input_type: Optional[str]):
        """Set what input we're waiting for from the user."""
        self.awaiting_input = input_type
        self.last_activity = datetime.now()
    
    def add_chat_turn(self, role: str, content: str, max_turns: int = 10):
        """Add a message to chat history, keeping only the last N turns."""
        self.chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # Trim to max turns (each turn = user + assistant = 2 entries)
        max_entries = max_turns * 2
        if len(self.chat_history) > max_entries:
            self.chat_history = self.chat_history[-max_entries:]
        self.last_activity = datetime.now()
    
    def get_vehicle_by_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Resolve pronoun references like "the first one", "#3", "that one".
        
        Args:
            reference: Natural language reference
            
        Returns:
            The referenced vehicle or None
        """
        reference_lower = reference.lower()
        
        # Check for "that one", "this one", "it" -> current vehicle
        if any(kw in reference_lower for kw in ["that one", "this one", "it", "this car", "that car"]):
            return self.current_vehicle
        
        # Check for numbered references: "#3", "number 3", "3rd", "about 3", or just "3"
        import re
        num_match = re.search(r'#(\d+)|number\s*(\d+)|(\d+)(?:st|nd|rd|th)|(?:about|vehicle|car)\s+(\d+)(?:\s|$)|^(\d+)$', reference_lower)
        if num_match:
            idx = int(num_match.group(1) or num_match.group(2) or num_match.group(3) or num_match.group(4) or num_match.group(5)) - 1
            if 0 <= idx < len(self.recent_vehicles):
                return self.recent_vehicles[idx]
        
        # Check for ordinal references
        if self.recent_vehicles:
            if "first" in reference_lower:
                return self.recent_vehicles[0] if len(self.recent_vehicles) > 0 else None
            if "second" in reference_lower:
                return self.recent_vehicles[1] if len(self.recent_vehicles) > 1 else None
            if "third" in reference_lower:
                return self.recent_vehicles[2] if len(self.recent_vehicles) > 2 else None
            if "fourth" in reference_lower:
                return self.recent_vehicles[3] if len(self.recent_vehicles) > 3 else None
            if "fifth" in reference_lower:
                return self.recent_vehicles[4] if len(self.recent_vehicles) > 4 else None
            if "last" in reference_lower:
                return self.recent_vehicles[-1] if self.recent_vehicles else None
        
        return None

    def record_disclosure(self, vehicle_id: int, disclosure_type: str, details: Dict[str, Any]) -> None:
        """Record that a disclosure was shown for a vehicle."""
        self.disclosures_shown[vehicle_id] = {
            "type": disclosure_type,
            "timestamp": datetime.now().isoformat(),
            **details
        }
        self.last_activity = datetime.now()

    def has_disclosure(self, vehicle_id: int, disclosure_type: Optional[str] = None) -> bool:
        """Check if a disclosure was shown for a vehicle."""
        if vehicle_id not in self.disclosures_shown:
            return False
        if disclosure_type:
            return self.disclosures_shown[vehicle_id].get("type") == disclosure_type
        return True

    def get_disclosure(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """Get disclosure record for a vehicle."""
        return self.disclosures_shown.get(vehicle_id)

    # T03: Credit tracking methods
    def set_credit_status(self, status: Dict[str, Any]) -> None:
        """Set credit status from credit evaluation."""
        self.credit_status = {
            **status,
            "timestamp": datetime.now().isoformat()
        }
        self.last_activity = datetime.now()

    def set_fcra_consent(self, consent: Dict[str, Any]) -> None:
        """Set FCRA consent record."""
        self.fcra_consent = consent
        self.last_activity = datetime.now()

    def set_customer_id(self, customer_id: str) -> None:
        """Set customer ID for credit operations."""
        self.customer_id = customer_id
        self.last_activity = datetime.now()

    def has_fcra_consent(self) -> bool:
        """Check if session has active FCRA consent."""
        return self.fcra_consent is not None


# In-memory session store
# In production, this would be Redis or database-backed
_sessions: Dict[str, SessionContext] = {}
_lock = asyncio.Lock()


async def get_session(session_id: str) -> SessionContext:
    """
    Get or create a session context.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        SessionContext for this session
    """
    async with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = SessionContext(session_id=session_id)
        
        session = _sessions[session_id]
        session.last_activity = datetime.now()
        return session


async def update_current_vehicle(session_id: str, vehicle: Dict[str, Any]) -> None:
    """
    Update the current vehicle for a session.
    
    Call this when a user views vehicle details.
    """
    session = await get_session(session_id)
    session.set_current_vehicle(vehicle)


async def update_recent_vehicles(session_id: str, vehicles: list) -> None:
    """
    Update the recent vehicles list for a session.
    
    Call this after showing search results.
    """
    session = await get_session(session_id)
    session.set_recent_vehicles(vehicles)


async def get_current_vehicle(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current vehicle for a session.
    
    Returns None if no vehicle has been discussed.
    """
    session = await get_session(session_id)
    return session.current_vehicle


async def resolve_vehicle_reference(session_id: str, reference: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a pronoun reference to a vehicle.
    
    Args:
        session_id: Session ID
        reference: Natural language reference like "that one", "the first one"
        
    Returns:
        The referenced vehicle or None
    """
    session = await get_session(session_id)
    return session.get_vehicle_by_reference(reference)


async def clear_session(session_id: str) -> None:
    """Clear a session (for testing or explicit reset)."""
    async with _lock:
        if session_id in _sessions:
            del _sessions[session_id]


async def update_last_payment(session_id: str, payment: Dict[str, Any]) -> None:
    """
    Store the last payment calculation result.
    
    Call this after a payment estimate is calculated.
    """
    session = await get_session(session_id)
    session.set_last_payment(payment)


async def get_last_payment(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the last payment calculation for a session.
    
    Returns None if no payment has been calculated.
    """
    session = await get_session(session_id)
    return session.last_payment


async def add_chat_message(session_id: str, role: str, content: str) -> None:
    """
    Add a message to the chat history.
    
    Args:
        session_id: Session ID
        role: Either 'user' or 'assistant'
        content: The message content
    """
    session = await get_session(session_id)
    session.add_chat_turn(role, content)


async def get_chat_history(session_id: str, max_turns: int = 5) -> list:
    """
    Get the recent chat history for a session.
    
    Args:
        session_id: Session ID
        max_turns: Maximum number of turns to return
        
    Returns:
        List of {role, content, timestamp} dicts
    """
    session = await get_session(session_id)
    # Return last N*2 entries (user + assistant = 1 turn)
    max_entries = max_turns * 2
    return session.chat_history[-max_entries:] if session.chat_history else []


async def get_session_count() -> int:
    """Get the number of active sessions."""
    return len(_sessions)


async def update_awaiting_input(session_id: str, input_type: Optional[str]) -> None:
    """
    Set what input we're waiting for from the user.
    
    Args:
        session_id: Session ID
        input_type: Type of input needed (e.g., "credit_info", "down_payment") or None to clear
    """
    session = await get_session(session_id)
    session.set_awaiting_input(input_type)


async def get_awaiting_input(session_id: str) -> Optional[str]:
    """
    Get what input we're waiting for from the user.
    
    Returns None if not waiting for specific input.
    """
    session = await get_session(session_id)
    return session.awaiting_input


async def clear_awaiting_input(session_id: str) -> None:
    """Clear the awaiting input state."""
    await update_awaiting_input(session_id, None)


# T02: Disclosure tracking functions

async def record_disclosure(
    session_id: str,
    vehicle_id: int,
    disclosure_type: str,
    details: Dict[str, Any]
) -> None:
    """
    Record that a disclosure was shown for a vehicle.

    Args:
        session_id: Session ID
        vehicle_id: Vehicle ID
        disclosure_type: Type of disclosure (e.g., "offering_price")
        details: Additional disclosure details
    """
    session = await get_session(session_id)
    session.record_disclosure(vehicle_id, disclosure_type, details)


async def has_disclosure(
    session_id: str,
    vehicle_id: int,
    disclosure_type: Optional[str] = None
) -> bool:
    """
    Check if a disclosure was shown for a vehicle.

    Args:
        session_id: Session ID
        vehicle_id: Vehicle ID
        disclosure_type: Optional type to check for

    Returns:
        True if disclosure was shown
    """
    session = await get_session(session_id)
    return session.has_disclosure(vehicle_id, disclosure_type)


async def get_disclosure(
    session_id: str,
    vehicle_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get disclosure record for a vehicle.

    Args:
        session_id: Session ID
        vehicle_id: Vehicle ID

    Returns:
        Disclosure record or None
    """
    session = await get_session(session_id)
    return session.get_disclosure(vehicle_id)


# T03: Credit tracking functions

async def set_credit_status(session_id: str, status: Dict[str, Any]) -> None:
    """
    Set credit status from credit evaluation.

    Args:
        session_id: Session ID
        status: Credit status dict with tier, decision, etc.
    """
    session = await get_session(session_id)
    session.set_credit_status(status)


async def get_credit_status(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get credit status for a session.

    Returns:
        Credit status dict or None
    """
    session = await get_session(session_id)
    return session.credit_status


async def set_fcra_consent(session_id: str, consent: Dict[str, Any]) -> None:
    """
    Set FCRA consent record for session.

    Args:
        session_id: Session ID
        consent: Consent record dict
    """
    session = await get_session(session_id)
    session.set_fcra_consent(consent)


async def get_fcra_consent(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get FCRA consent record for session.

    Returns:
        Consent record or None
    """
    session = await get_session(session_id)
    return session.fcra_consent


async def has_fcra_consent(session_id: str) -> bool:
    """
    Check if session has active FCRA consent.

    Returns:
        True if consent exists
    """
    session = await get_session(session_id)
    return session.has_fcra_consent()


async def set_customer_id(session_id: str, customer_id: str) -> None:
    """
    Set customer ID for credit operations.

    Args:
        session_id: Session ID
        customer_id: Customer ID
    """
    session = await get_session(session_id)
    session.set_customer_id(customer_id)


async def get_customer_id(session_id: str) -> Optional[str]:
    """
    Get customer ID for session.

    Returns:
        Customer ID or None
    """
    session = await get_session(session_id)
    return session.customer_id
