"""
Compliance Log Pydantic models.

Per 03_implementation_dummy_data_plan.md §1.4 ComplianceLog (Regulatory Event Entity)
Per 02_strategic_blueprint.md §3.2.2 Regulatory Audit Log Schema
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import re
import uuid


class EventType(str, Enum):
    """Compliance event types for audit logging."""
    RATE_INQUIRY = "rate_inquiry"
    SOFT_PULL_CONSENT = "soft_pull_consent"
    HARD_PULL_CONSENT = "hard_pull_consent"
    ADVERSE_ACTION_GENERATED = "adverse_action_generated"
    DISCLOSURE_PRESENTED = "disclosure_presented"
    DEAL_CREATED = "deal_created"
    DEAL_MODIFIED = "deal_modified"
    PAYMENT_CALCULATED = "payment_calculated"


class Actor(str, Enum):
    """Actor types for audit attribution."""
    USER = "user"
    AGENT_CONVERSATIONALIST = "agent:conversationalist"
    AGENT_FIN_CALC = "agent:fin_calc"
    AGENT_COMPLIANCE = "agent:compliance"
    AGENT_CREDIT_OFFICER = "agent:credit_officer"
    AGENT_INVENTORY_GRAPH = "agent:inventory_graph"
    SYSTEM = "system"


class AdverseActionReason(BaseModel):
    """
    Regulation B reason code for adverse action.

    Per CFPB Circular 2023-03: Cannot use generic reasons like
    "Credit Score" or "Internal Policy".
    """
    code: str = Field(..., pattern=r'^[A-Z]\d{2}$')  # e.g., "A01", "B02"
    text: str

    @field_validator('code', mode='before')
    @classmethod
    def validate_code_format(cls, v):
        if not re.match(r'^[A-Z]\d{2}$', v):
            raise ValueError('Reason code must be in format X00 (e.g., A01, B02)')
        return v


class CreditDataUsed(BaseModel):
    """Credit bureau data used in decision."""
    bureau_source: str  # Equifax | Experian | TransUnion
    score_date: date
    credit_score: int = Field(..., ge=300, le=850)


class NoticeDetails(BaseModel):
    """Details about notice delivery for compliance tracking."""
    notice_generated: bool = False
    notice_sent_method: Optional[str] = None  # email | mail | download
    notice_sent_timestamp: Optional[datetime] = None
    email_message_id: Optional[str] = None
    postal_tracking: Optional[str] = None


class RegulatoryFlags(BaseModel):
    """Regulatory compliance flags for audit entries."""
    fcra_compliant: Optional[bool] = None
    sb766_disclosure_verified: Optional[bool] = None
    adverse_action_reason_code: Optional[str] = None
    ecoa_compliant: Optional[bool] = None
    glba_compliant: Optional[bool] = None


class ContextSnapshot(BaseModel):
    """Context snapshot for audit entries."""
    active_rate_sheet_id: Optional[str] = None
    user_location_ip: Optional[str] = None
    session_id: Optional[str] = None
    vehicle_id: Optional[int] = None
    customer_id: Optional[str] = None


class ComplianceLog(BaseModel):
    """
    Regulatory event/compliance log entity.

    Per 03_implementation_dummy_data_plan.md §1.4:
    - Tracks Adverse Actions and other mandated disclosures
    - The "black box" recorder for dealership's compliance posture
    - Reason codes must map to Reg B specific codes
    """
    log_id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:8]}")
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Attribution
    actor: Actor = Actor.SYSTEM
    event_type: EventType

    # Related entities
    related_deal_id: Optional[str] = None
    customer_id: Optional[str] = None
    session_id: Optional[str] = None

    # Payload hash for tamper evidence (SHA-256)
    payload_hash: Optional[str] = None

    # Credit data (for adverse actions)
    credit_data_used: Optional[CreditDataUsed] = None

    # Denial reasons (up to 4 per Reg B)
    denial_reasons: List[AdverseActionReason] = Field(default_factory=list)

    # Notice tracking
    notice_details: Optional[NoticeDetails] = None

    # Context snapshot
    context_snapshot: Optional[ContextSnapshot] = None

    # Regulatory flags
    regulatory_flags: Optional[RegulatoryFlags] = None

    @field_validator('payload_hash', mode='before')
    @classmethod
    def validate_payload_hash(cls, v):
        if v is None:
            return None
        # SHA-256 hash should be 64 hex characters
        if not re.match(r'^[a-f0-9]{64}$', v.lower()):
            raise ValueError('payload_hash must be a 64-character SHA-256 hex string')
        return v.lower()

    @field_validator('denial_reasons', mode='before')
    @classmethod
    def validate_denial_reasons(cls, v):
        if v is None:
            return []
        if len(v) > 4:
            raise ValueError('Maximum 4 denial reasons allowed per Regulation B')
        return v

    @model_validator(mode='after')
    def validate_adverse_action(self):
        """Validate adverse action requirements."""
        if self.event_type == EventType.ADVERSE_ACTION_GENERATED:
            if not self.denial_reasons:
                raise ValueError(
                    'Adverse action events must include at least one denial reason'
                )
            if not self.credit_data_used:
                raise ValueError(
                    'Adverse action events must include credit_data_used'
                )
        return self

    model_config = ConfigDict(from_attributes=True)


class ComplianceLogCreate(BaseModel):
    """Schema for creating a new compliance log entry."""
    event_type: EventType
    actor: Actor = Actor.SYSTEM
    related_deal_id: Optional[str] = None
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    payload_hash: Optional[str] = None

    @field_validator('payload_hash', mode='before')
    @classmethod
    def validate_payload_hash(cls, v):
        if v is None:
            return None
        if not re.match(r'^[a-f0-9]{64}$', v.lower()):
            raise ValueError('payload_hash must be a 64-character SHA-256 hex string')
        return v.lower()


class AuditLogEntry(BaseModel):
    """
    Generic audit log entry for database storage.

    Maps to audit_logs table with extended fields.
    """
    id: Optional[int] = None
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    user_input: Optional[str] = None
    request_params: Optional[str] = None  # JSON string
    response_data: Optional[str] = None   # JSON string
    rule_id: Optional[str] = None
    calculation_trace: Optional[str] = None  # JSON string
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None

    # Extended fields (per migration 004)
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    actor: Optional[str] = None
    event_type: Optional[str] = None
    payload_hash: Optional[str] = None
    regulatory_flags: Optional[str] = None  # JSON string

    @field_validator('payload_hash', mode='before')
    @classmethod
    def validate_payload_hash(cls, v):
        if v is None:
            return None
        if not re.match(r'^[a-f0-9]{64}$', v.lower()):
            raise ValueError('payload_hash must be a 64-character SHA-256 hex string')
        return v.lower()

    model_config = ConfigDict(from_attributes=True)
