"""
T02: Core Compliance Models

Pydantic models for SB 766 / CARS Act compliance enforcement.
Per tasks/T02_core_compliance.md
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ComplianceViolation(BaseModel):
    """
    Represents a compliance violation that blocks an action.
    """
    code: str  # e.g., "SB766_OFFERING_PRICE_REQUIRED"
    regulation: str  # e.g., "California SB 766"
    message: str
    blocked_action: str  # What was prevented
    required_disclosure: Optional[str] = None


class ComplianceCheckResult(BaseModel):
    """
    Result of a compliance check.
    """
    allowed: bool
    violation: Optional[ComplianceViolation] = None
    required_action: Optional[str] = None  # e.g., "SHOW_OFFERING_PRICE"


class AddOnValidationResult(BaseModel):
    """
    Result of add-on validation against CARS Act rules.
    """
    valid: bool
    addon_id: str
    addon_name: str
    reason: Optional[str] = None  # Why blocked
    regulation: Optional[str] = None  # e.g., "CARS Act Valueless Add-on"


class DisclosureType(str, Enum):
    """Types of regulatory disclosures."""
    OFFERING_PRICE = "offering_price"
    ADVERSE_ACTION = "adverse_action"
    FCRA_CONSENT = "fcra_consent"


class DisclosureRecord(BaseModel):
    """
    Record of a disclosure shown to a customer.
    """
    disclosure_id: str
    disclosure_type: DisclosureType
    session_id: str
    vehicle_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    offering_price: Optional[float] = None
    components: Optional[dict] = None
    payload_hash: Optional[str] = None


class ComplianceEvent(BaseModel):
    """
    Audit log entry for compliance events.
    """
    transaction_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = "agent:compliance"
    event_type: str
    payload_hash: Optional[str] = None
    regulatory_flags: dict = Field(default_factory=dict)
    session_id: Optional[str] = None
    vehicle_id: Optional[int] = None
    details: Optional[dict] = None
