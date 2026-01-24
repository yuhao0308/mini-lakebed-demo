"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums
class VehicleStatus(str, Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    RESERVED = "reserved"


class BodyStyle(str, Enum):
    SEDAN = "sedan"
    SUV = "suv"
    TRUCK = "truck"
    COUPE = "coupe"
    HATCHBACK = "hatchback"
    WAGON = "wagon"
    CONVERTIBLE = "convertible"
    VAN = "van"


class CreditTier(str, Enum):
    SUPER_PRIME = "super_prime"
    PRIME = "prime"
    NEAR_PRIME = "near_prime"
    SUBPRIME = "subprime"
    DEEP_SUBPRIME = "deep_subprime"


class DaysBasis(str, Enum):
    """Interest calculation day-count convention."""
    THIRTY_360 = "30/360"
    ACTUAL_365 = "actual/365"
    BANK_365_360 = "365/360"


class FuelType(str, Enum):
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"


# Vehicle Models
class VehicleBase(BaseModel):
    make: str
    model: str
    year: int
    trim: Optional[str] = None
    body_style: BodyStyle
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    mileage: int = 0
    price: float
    msrp: Optional[float] = None
    fuel_type: FuelType = FuelType.GASOLINE
    transmission: str = "automatic"
    drivetrain: str = "FWD"
    engine: Optional[str] = None
    description: Optional[str] = None


class Vehicle(VehicleBase):
    id: int
    vin: str
    status: VehicleStatus = VehicleStatus.AVAILABLE
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VehicleSearchParams(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    body_style: Optional[BodyStyle] = None
    max_mileage: Optional[int] = None
    fuel_type: Optional[FuelType] = None
    limit: int = Field(default=10, le=50)


class VehicleSearchResponse(BaseModel):
    count: int
    vehicles: List[Vehicle]


# Lender Rule Models
class LenderRule(BaseModel):
    id: int
    rule_id: str
    lender_name: str
    program_name: Optional[str] = None
    credit_tier: CreditTier
    min_fico: int
    max_fico: int
    min_term_months: int
    max_term_months: int
    base_apr: float
    max_ltv: float
    min_loan_amount: float
    max_loan_amount: float
    doc_fee: float = 0
    is_demo: bool = True

    class Config:
        from_attributes = True


# Payment Models
class PaymentRequest(BaseModel):
    vehicle_id: int
    down_payment: float = Field(ge=0, description="Down payment amount in USD")
    credit_tier: CreditTier
    fico_estimate: int = Field(ge=300, le=850, description="Estimated FICO score")
    term_months: int = Field(ge=12, le=84, description="Loan term in months")


class CalculationTrace(BaseModel):
    vehicle_price: float
    down_payment: float
    principal: float
    monthly_rate: float
    formula: str = "P × [r(1+r)^n] / [(1+r)^n – 1]"


class PaymentAudit(BaseModel):
    rule_id: str
    lender: str
    matched_criteria: dict
    calculation_trace: CalculationTrace


class PaymentEstimate(BaseModel):
    monthly_payment: float
    apr: float
    term_months: int
    principal: float
    total_interest: float
    total_cost: float


class PaymentResponse(BaseModel):
    success: bool = True
    estimate: PaymentEstimate
    audit: PaymentAudit
    disclaimer: str = "⚠️ DEMO ONLY: Synthetic lender rules for demonstration purposes. Not a commitment to lend."


class PaymentErrorResponse(BaseModel):
    success: bool = False
    error: dict


# Chat Models
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ToolCall(BaseModel):
    tool: str
    params: dict
    result_count: Optional[int] = None


class ChatMetadata(BaseModel):
    intent: str
    processing_time_ms: int


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: List[ToolCall] = []
    metadata: ChatMetadata


# Health Models
class ComponentStatus(BaseModel):
    database: str
    llm: str
    vector_store: str


class HealthResponse(BaseModel):
    status: str
    version: str
    components: ComponentStatus


# ============================================================================
# T01: Data Foundation Models
# Per 03_implementation_dummy_data_plan.md
# ============================================================================

class AddOn(BaseModel):
    """
    Vehicle add-on with benefit tracking.

    Per SB 766 / CARS Act: Add-ons must have documented benefit.
    """
    add_on_id: str
    name: str
    price: float = Field(..., ge=0)
    benefit_statement: Optional[str] = None
    compliance_check_passed: bool = False


class OfferingPriceComponents(BaseModel):
    """
    SB 766 compliant offering price breakdown.

    Per spec: Offering Price = base + doc_fee + mandatory_addons
    Does NOT include taxes/registration (government charges).
    """
    base_vehicle_price: float = Field(..., ge=0)
    doc_fee: float = Field(default=0, ge=0)
    mandatory_addons: List[AddOn] = Field(default_factory=list)
    total_offering_price: float = Field(..., ge=0)


class TradeIn(BaseModel):
    """
    Trade-in vehicle details.

    Per spec: If a customer owes $18k on a car worth $15k,
    the $3k deficit is added to the new loan (negative equity).
    """
    has_trade: bool = False
    allowance: float = Field(default=0, ge=0)
    payoff_amount: float = Field(default=0, ge=0)
    equity_amount: float = 0
    negative_equity_financed: float = Field(default=0, ge=0)
    vin: Optional[str] = None


class TaxCalculation(BaseModel):
    """
    Tax calculation details.

    Per spec §4.2: CA taxes full price; AZ allows trade-in credit.
    """
    jurisdiction_code: str
    tax_rate_combined: float = Field(..., ge=0, le=1)
    taxable_basis: float = Field(..., ge=0)
    total_sales_tax: float = Field(..., ge=0)
    rule_applied: str


class TaxRate(BaseModel):
    """Tax jurisdiction reference data."""
    zip_code: str
    state: str
    city: str
    county: str
    county_rate: float
    city_rate: float
    state_rate: float
    combined_rate: float
    special_district_rate: float = 0
    tax_basis_rule: str
    trade_in_credit: bool

    class Config:
        from_attributes = True


class AdverseActionCode(BaseModel):
    """Regulation B adverse action reason code."""
    code: str
    text: str

    class Config:
        from_attributes = True


class LenderRuleExtended(LenderRule):
    """Extended lender rule with T01 fields."""
    days_basis: DaysBasis = DaysBasis.THIRTY_360
    dealer_reserve_cap: float = 2.5
    stips_required: Optional[List[str]] = None

    class Config:
        from_attributes = True
