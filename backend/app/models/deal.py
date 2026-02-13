"""
Deal Jacket Pydantic models.

Per 03_implementation_dummy_data_plan.md §1.3 DealJacket
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DealStatus(str, Enum):
    """Deal lifecycle status."""
    WORKING = "working"
    DESKED = "desked"
    CONTRACTED = "contracted"
    FUNDED = "funded"
    UNWOUND = "unwound"


class DealType(str, Enum):
    """Type of deal/transaction."""
    RETAIL_FINANCE = "retail_finance"
    LEASE = "lease"
    CASH = "cash"


class DaysBasis(str, Enum):
    """Interest calculation day-count convention."""
    THIRTY_360 = "30/360"
    ACTUAL_365 = "actual/365"
    BANK_365_360 = "365/360"


class TradeIn(BaseModel):
    """
    Trade-in vehicle details.

    Per spec: If a customer owes $18k on a car worth $15k,
    the $3k deficit is added to the new loan (negative equity).
    """
    has_trade: bool = False
    allowance: float = Field(default=0, ge=0)
    payoff_amount: float = Field(default=0, ge=0)
    equity_amount: float = 0  # Calculated: allowance - payoff
    negative_equity_financed: float = Field(default=0, ge=0)
    vin: Optional[str] = None

    @model_validator(mode='after')
    def calculate_equity(self):
        if self.has_trade:
            self.equity_amount = self.allowance - self.payoff_amount
            if self.equity_amount < 0:
                self.negative_equity_financed = abs(self.equity_amount)
                self.equity_amount = 0
        return self


class TaxCalculation(BaseModel):
    """
    Tax calculation details.

    Per spec §4.2: CA taxes full price; AZ allows trade-in credit.
    """
    jurisdiction_code: str  # e.g., "CA_SAN_DIEGO_92101"
    tax_rate_combined: float = Field(..., ge=0, le=1)
    taxable_basis: float = Field(..., ge=0)
    total_sales_tax: float = Field(..., ge=0)
    rule_applied: str  # e.g., "CA_FULL_PRICE_BASIS" or "AZ_TRADE_IN_CREDIT"


class DealFees(BaseModel):
    """Deal fee breakdown."""
    doc_fee: float = Field(default=0, ge=0)
    license_fee: float = Field(default=0, ge=0)
    registration_fee: float = Field(default=0, ge=0)
    electronic_filing_fee: float = Field(default=0, ge=0)
    total_fees: float = Field(default=0, ge=0)

    @model_validator(mode='after')
    def calculate_total(self):
        self.total_fees = (
            self.doc_fee +
            self.license_fee +
            self.registration_fee +
            self.electronic_filing_fee
        )
        return self


class LendingTerms(BaseModel):
    """
    Lending/financing terms.

    Per spec: All fields must be precise for Regulation Z compliance.
    """
    lender_id: str
    program_tier: str
    term_months: int = Field(..., ge=12, le=84)
    buy_rate: float = Field(..., ge=0)
    contract_apr: float = Field(..., ge=0)
    dealer_reserve: float = Field(default=0, ge=0)
    days_basis: DaysBasis = DaysBasis.THIRTY_360
    amount_financed: float = Field(..., ge=0)
    monthly_payment: float = Field(..., ge=0)
    total_of_payments: float = Field(..., ge=0)
    finance_charge: float = Field(..., ge=0)


class AuditTrailEntry(BaseModel):
    """Individual audit trail entry for deal changes."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    action: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None


class DealJacket(BaseModel):
    """
    Full deal structure entity.

    Per 03_implementation_dummy_data_plan.md §1.3:
    The most complex schema handling penny-perfect math and structural compliance.
    """
    deal_id: str
    customer_id: str
    vehicle_id: int
    deal_status: DealStatus = DealStatus.WORKING
    deal_type: DealType = DealType.RETAIL_FINANCE
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Financial Structure
    selling_price: float = Field(..., gt=0)
    sb766_offering_price: Optional[float] = None
    rebates_total: float = Field(default=0, ge=0)
    cash_down_payment: float = Field(default=0, ge=0)

    # Nested structures
    trade_in: Optional[TradeIn] = None
    tax_calculation: Optional[TaxCalculation] = None
    fees: Optional[DealFees] = None
    lending_terms: Optional[LendingTerms] = None

    # Audit trail
    audit_trail: List[AuditTrailEntry] = Field(default_factory=list)

    @field_validator('selling_price', mode='before')
    @classmethod
    def validate_selling_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Selling price cannot be negative')
        return v

    @model_validator(mode='after')
    def set_offering_price(self):
        if self.sb766_offering_price is None:
            self.sb766_offering_price = self.selling_price
        return self

    model_config = ConfigDict(from_attributes=True)


class DealCreate(BaseModel):
    """Schema for creating a new deal."""
    customer_id: str
    vehicle_id: int
    deal_type: DealType = DealType.RETAIL_FINANCE
    selling_price: float = Field(..., gt=0)
    cash_down_payment: float = Field(default=0, ge=0)
    rebates_total: float = Field(default=0, ge=0)

    @field_validator('selling_price', mode='before')
    @classmethod
    def validate_selling_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Selling price cannot be negative')
        return v


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

    @model_validator(mode='after')
    def validate_benefit_compliance(self):
        """
        Per spec: AddOn with benefit_statement=None and
        compliance_check_passed=True is invalid.
        """
        if self.compliance_check_passed and not self.benefit_statement:
            raise ValueError(
                'Add-on cannot have compliance_check_passed=True '
                'without a benefit_statement'
            )
        return self


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

    @model_validator(mode='after')
    def validate_total(self):
        calculated = (
            self.base_vehicle_price +
            self.doc_fee +
            sum(addon.price for addon in self.mandatory_addons)
        )
        # Allow small floating point tolerance
        if abs(calculated - self.total_offering_price) > 0.01:
            raise ValueError(
                f'total_offering_price ({self.total_offering_price}) does not match '
                f'calculated total ({calculated})'
            )
        return self
