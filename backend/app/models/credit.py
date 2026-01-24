"""
T03: Credit Flow Models

Pydantic models for FCRA consent, credit decisions, and Reg B adverse actions.
Per tasks/T03_credit_flow.md
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ConsentType(str, Enum):
    """FCRA consent types."""
    SOFT_PULL = "soft_pull"
    HARD_PULL = "hard_pull"


class CreditTier(str, Enum):
    """Credit tier classification based on FICO score."""
    SUPER_PRIME = "super_prime"  # 750+
    PRIME = "prime"              # 700-749
    NEAR_PRIME = "near_prime"    # 650-699
    SUBPRIME = "subprime"        # 600-649
    DEEP_SUBPRIME = "deep_subprime"  # 550-599
    DECLINE = "decline"          # <550


class ConsentRecord(BaseModel):
    """FCRA consent record with full audit trail."""
    consent_id: str
    customer_id: str
    consent_type: ConsentType
    granted_at: datetime
    ip_address: str
    user_agent: str
    legal_text_version: str
    expires_at: datetime


class ConsentCheckResult(BaseModel):
    """Result of checking for valid FCRA consent."""
    valid: bool
    requires_consent: bool = False
    consent: Optional[ConsentRecord] = None
    message: Optional[str] = None


class ConsentRequest(BaseModel):
    """Request to record FCRA consent."""
    customer_id: str
    consent_type: ConsentType = ConsentType.SOFT_PULL
    legal_text_version: str = "v2026.1"


class ConsentResponse(BaseModel):
    """Response after recording consent."""
    success: bool
    consent_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class CreditTierResult(BaseModel):
    """Result of credit tier assignment."""
    tier: CreditTier
    fico_score: int
    tier_boundaries: dict = Field(default_factory=dict)


class RequestedTerms(BaseModel):
    """Terms requested by customer."""
    vehicle_price: float
    down_payment: float
    term_months: int
    trade_in_value: float = 0


class ApprovedTerms(BaseModel):
    """Approved loan terms."""
    principal: float
    apr: float
    term_months: int
    monthly_payment: float
    lender_name: str
    rule_id: str


class AdverseActionReason(BaseModel):
    """Regulation B adverse action reason."""
    code: str  # e.g., "A01"
    text: str  # e.g., "Income insufficient for amount of credit requested"


class CounterOffer(BaseModel):
    """Counter-offer for conditional approval."""
    required_down_payment: float
    approved_apr: float
    approved_term: int
    monthly_payment: float
    message: str  # Human-readable explanation


class LenderConstraints(BaseModel):
    """Lender constraints that triggered counter-offer."""
    max_ltv: float
    max_term: int
    min_down_payment: float
    apr: float


class CreditDecision(BaseModel):
    """Full credit decision result."""
    decision: str  # approved | conditional | declined
    tier: CreditTier
    fico_score: int
    approved_terms: Optional[ApprovedTerms] = None
    conditions: Optional[List[str]] = None  # Required stips
    decline_reasons: Optional[List[AdverseActionReason]] = None
    counter_offer: Optional[CounterOffer] = None
    bureau_source: str = "Experian"
    score_date: date = Field(default_factory=date.today)


class AdverseActionNotice(BaseModel):
    """Formal Reg B adverse action notice."""
    notice_id: str
    customer_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    bureau_source: str  # Equifax | Experian | TransUnion
    score_date: date
    fico_score: int
    principal_reasons: List[AdverseActionReason] = Field(max_length=4)
    counter_offer: Optional[CounterOffer] = None
    pdf_url: Optional[str] = None


class NoticeDeliveryResult(BaseModel):
    """Result of adverse action notice delivery."""
    success: bool
    delivery_method: str  # email | mail | download
    delivered_at: datetime = Field(default_factory=datetime.utcnow)
    tracking_id: Optional[str] = None
    error: Optional[str] = None
