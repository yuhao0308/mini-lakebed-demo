"""
Customer Profile Pydantic models.

Per 03_implementation_dummy_data_plan.md §1.1 CustomerProfile
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import re
import uuid


class PIIClearanceLevel(str, Enum):
    """PII access clearance levels for data masking."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH_SENSITIVITY = "high_sensitivity"


class ResidenceType(str, Enum):
    """Customer residence ownership type."""
    OWN = "own"
    RENT = "rent"
    OTHER = "other"


class ConsentType(str, Enum):
    """FCRA consent types."""
    SOFT_PULL = "soft_pull"
    HARD_PULL = "hard_pull"


class FCRAConsentEntry(BaseModel):
    """
    Individual FCRA consent record.

    Per spec: Consent is temporal; a customer may consent today,
    the consent expires in 30 days, and they must re-consent.
    """
    consent_id: str
    consent_type: ConsentType
    granted_at: datetime
    ip_address: str
    user_agent: Optional[str] = None
    legal_text_version: str = "v2026.1"
    expires_at: datetime

    @field_validator('consent_id', mode='before')
    @classmethod
    def generate_consent_id(cls, v):
        if not v:
            return f"consent_{uuid.uuid4().hex[:8]}"
        return v


class CustomerIdentity(BaseModel):
    """Customer identity information (potentially PII)."""
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    middle_initial: Optional[str] = None
    email: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_type: Optional[str] = None
    date_of_birth: Optional[date] = None
    ssn_masked: Optional[str] = None  # ***-**-1234
    ssn_token: Optional[str] = None   # vault reference

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v is None or v == "":
            return None
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v

    @field_validator('ssn_masked', mode='before')
    @classmethod
    def validate_ssn_masked(cls, v):
        if v is None:
            return None
        # Should be in format ***-**-XXXX
        if not re.match(r'^\*{3}-\*{2}-\d{4}$', v):
            raise ValueError('SSN masked must be in format ***-**-XXXX')
        return v


class CustomerResidence(BaseModel):
    """Customer residence information."""
    street: Optional[str] = None
    unit: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None
    years_at_residence: Optional[int] = None
    months_at_residence: Optional[int] = None
    residence_type: Optional[ResidenceType] = None


class CustomerEmployment(BaseModel):
    """Customer employment information."""
    employer_name: Optional[str] = None
    job_title: Optional[str] = None
    years_employed: Optional[int] = None
    monthly_gross_income: Optional[float] = Field(None, ge=0)
    income_verification_status: Optional[str] = None
    other_income: Optional[float] = Field(default=0, ge=0)


class CustomerProfile(BaseModel):
    """
    Full customer profile entity.

    Per 03_implementation_dummy_data_plan.md §1.1:
    - UUID v4 is mandatory for ID
    - fcra_consent_log is modeled as a nested array of objects
    - pii_clearance_level dictates visibility
    """
    customer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_system: Optional[str] = None
    pii_clearance_level: PIIClearanceLevel = PIIClearanceLevel.HIGH_SENSITIVITY

    # Nested components
    identity: CustomerIdentity
    residence: Optional[CustomerResidence] = None
    employment: Optional[CustomerEmployment] = None
    fcra_consent_log: List[FCRAConsentEntry] = Field(default_factory=list)

    @field_validator('customer_id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        if v is None:
            return str(uuid.uuid4())
        # Validate UUID v4 format
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError('Customer ID must be a valid UUID v4')
        return v

    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: Optional[str] = None
    phone_primary: Optional[str] = None
    date_of_birth: Optional[date] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    residence_type: Optional[ResidenceType] = None
    employer_name: Optional[str] = None
    monthly_gross_income: Optional[float] = None
    source_system: Optional[str] = None

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v is None or v == "":
            return None
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v
