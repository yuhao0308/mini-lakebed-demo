"""
T02: Disclosure Tracker Service

Tracks which regulatory disclosures have been presented per session.
Per tasks/T02_core_compliance.md
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import asyncio

from app.models.compliance import DisclosureRecord, DisclosureType
from app.models.schemas import OfferingPriceComponents


# In-memory disclosure store
# Key: session_id -> Dict[vehicle_id -> DisclosureRecord]
_disclosures: Dict[str, Dict[int, DisclosureRecord]] = {}
_lock = asyncio.Lock()


class DisclosureTracker:
    """
    Track which regulatory disclosures have been presented per session.
    """

    async def record_offering_price_shown(
        self,
        session_id: str,
        vehicle_id: int,
        offering_price: float,
        components: OfferingPriceComponents
    ) -> str:
        """
        Record that offering price was disclosed.
        Returns disclosure_id for audit trail.
        """
        async with _lock:
            if session_id not in _disclosures:
                _disclosures[session_id] = {}

            disclosure_id = str(uuid.uuid4())

            # Create payload hash for audit trail
            payload = {
                "vehicle_id": vehicle_id,
                "offering_price": offering_price,
                "components": components.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            }
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest()

            record = DisclosureRecord(
                disclosure_id=disclosure_id,
                disclosure_type=DisclosureType.OFFERING_PRICE,
                session_id=session_id,
                vehicle_id=vehicle_id,
                timestamp=datetime.utcnow(),
                offering_price=offering_price,
                components=components.model_dump(),
                payload_hash=payload_hash
            )

            _disclosures[session_id][vehicle_id] = record

            return disclosure_id

    async def has_offering_price_been_shown(
        self,
        session_id: str,
        vehicle_id: int
    ) -> bool:
        """Check if offering price was disclosed for this vehicle in this session."""
        async with _lock:
            if session_id not in _disclosures:
                return False
            return vehicle_id in _disclosures[session_id]

    async def get_disclosure_record(
        self,
        session_id: str,
        vehicle_id: int
    ) -> Optional[DisclosureRecord]:
        """Get disclosure record for a specific vehicle in a session."""
        async with _lock:
            if session_id not in _disclosures:
                return None
            return _disclosures[session_id].get(vehicle_id)

    async def get_disclosure_audit(
        self,
        session_id: str
    ) -> List[DisclosureRecord]:
        """Get all disclosures for session (for audit log)."""
        async with _lock:
            if session_id not in _disclosures:
                return []
            return list(_disclosures[session_id].values())

    async def clear_session_disclosures(
        self,
        session_id: str
    ) -> None:
        """Clear all disclosures for a session (for testing)."""
        async with _lock:
            if session_id in _disclosures:
                del _disclosures[session_id]


# Module-level helper functions for convenience
async def record_offering_price(
    session_id: str,
    vehicle_id: int,
    offering_price: float,
    components: OfferingPriceComponents
) -> str:
    """Record offering price disclosure."""
    tracker = DisclosureTracker()
    return await tracker.record_offering_price_shown(
        session_id, vehicle_id, offering_price, components
    )


async def check_offering_price_disclosed(
    session_id: str,
    vehicle_id: int
) -> bool:
    """Check if offering price was disclosed."""
    tracker = DisclosureTracker()
    return await tracker.has_offering_price_been_shown(session_id, vehicle_id)


async def get_session_disclosures(session_id: str) -> List[DisclosureRecord]:
    """Get all disclosures for a session."""
    tracker = DisclosureTracker()
    return await tracker.get_disclosure_audit(session_id)


async def clear_disclosures(session_id: str) -> None:
    """Clear disclosures for a session."""
    tracker = DisclosureTracker()
    await tracker.clear_session_disclosures(session_id)
