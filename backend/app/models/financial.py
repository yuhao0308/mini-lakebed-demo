"""
T04: Financial Models with Decimal Precision

Pydantic models with Decimal fields for penny-perfect calculations.
Per tasks/T04_math_precision.md
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any, Annotated
from pydantic import BaseModel, Field, field_validator, BeforeValidator
from datetime import datetime

from app.services.day_count import DayCountMethod


# Validation helpers
def validate_money(v: Any) -> Decimal:
    """Validate and convert to money (2 decimal places)."""
    if v is None:
        return Decimal("0.00")
    if isinstance(v, Decimal):
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_rate(v: Any) -> Decimal:
    """Validate and convert to rate (4 decimal places)."""
    if v is None:
        return Decimal("0.0000")
    if isinstance(v, Decimal):
        return v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def validate_decimal(v: Any) -> Decimal:
    """Validate and convert to Decimal."""
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# Annotated types for Pydantic v2
MoneyField = Annotated[Decimal, BeforeValidator(validate_money)]
RateField = Annotated[Decimal, BeforeValidator(validate_rate)]
DecimalField = Annotated[Decimal, BeforeValidator(validate_decimal)]


class TradeInDetails(BaseModel):
    """Trade-in vehicle details with Decimal precision."""
    has_trade: bool = False
    allowance: MoneyField = Field(default=Decimal("0.00"), description="Trade-in allowance offered")
    payoff_amount: MoneyField = Field(default=Decimal("0.00"), description="Amount owed on trade-in")
    equity_amount: MoneyField = Field(default=Decimal("0.00"), description="Equity: allowance - payoff")
    negative_equity_financed: MoneyField = Field(default=Decimal("0.00"), description="Negative equity added to loan")
    vin: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        """Calculate equity after initialization."""
        if self.has_trade:
            equity = self.allowance - self.payoff_amount
            if equity >= 0:
                self.equity_amount = equity
                self.negative_equity_financed = Decimal("0.00")
            else:
                self.equity_amount = Decimal("0.00")
                self.negative_equity_financed = abs(equity)


class FeeBreakdown(BaseModel):
    """Fee breakdown with Decimal precision."""
    doc_fee: MoneyField = Field(default=Decimal("0.00"), description="Documentation fee")
    license_fee: MoneyField = Field(default=Decimal("0.00"), description="License/title fee")
    registration_fee: MoneyField = Field(default=Decimal("0.00"), description="Registration fee")
    total_fees: MoneyField = Field(default=Decimal("0.00"), description="Total of all fees")

    def calculate_total(self) -> Decimal:
        """Calculate total fees."""
        self.total_fees = self.doc_fee + self.license_fee + self.registration_fee
        return self.total_fees


class TaxBreakdown(BaseModel):
    """Tax breakdown with Decimal precision."""
    jurisdiction_code: str = Field(description="ZIP code or jurisdiction ID")
    state: str = Field(description="State code")
    tax_rate_combined: RateField = Field(description="Combined tax rate as percentage")
    taxable_basis: MoneyField = Field(description="Amount subject to tax")
    total_sales_tax: MoneyField = Field(description="Calculated tax amount")
    rule_applied: str = Field(description="Tax rule explanation")
    trade_in_credit_applied: bool = Field(default=False, description="Whether trade-in reduced taxable basis")


class LendingTerms(BaseModel):
    """Lending terms with Decimal precision."""
    lender_id: str = Field(description="Lender rule ID")
    lender_name: str = Field(description="Lender name")
    program_tier: str = Field(description="Credit tier (super_prime, prime, etc.)")
    term_months: int = Field(description="Loan term in months")
    buy_rate: RateField = Field(description="Lender's buy rate APR")
    contract_apr: RateField = Field(description="Contract APR (buy rate + dealer reserve)")
    dealer_reserve: RateField = Field(default=Decimal("0.0000"), description="Dealer markup")
    days_basis: str = Field(default="30/360", description="Day count method")
    amount_financed: MoneyField = Field(description="Total loan amount")
    monthly_payment: MoneyField = Field(description="Monthly payment amount")
    total_of_payments: MoneyField = Field(description="Monthly × term")
    finance_charge: MoneyField = Field(description="Total interest (total_of_payments - amount_financed)")


class DealSummary(BaseModel):
    """
    Complete deal summary with penny-perfect calculations.

    Per 03_implementation_dummy_data_plan.md §1.3 DealJacket schema
    """
    # Identification
    deal_id: Optional[str] = None
    vehicle_id: int
    customer_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Pricing
    selling_price: MoneyField = Field(description="Vehicle selling price")
    sb766_offering_price: MoneyField = Field(description="SB 766 disclosed offering price")
    rebates_total: MoneyField = Field(default=Decimal("0.00"), description="Total rebates")

    # Down payment / Trade
    cash_down_payment: MoneyField = Field(default=Decimal("0.00"), description="Cash down payment")
    trade_in: Optional[TradeInDetails] = None

    # Tax
    tax: TaxBreakdown

    # Fees
    fees: FeeBreakdown

    # Lending
    lending: LendingTerms

    # Validation results
    ltv: RateField = Field(description="Loan-to-value ratio")
    payment_packing_verified: bool = Field(default=False, description="monthly × term == total_of_payments")


class PaymentEstimate(BaseModel):
    """Payment estimate response with Decimal precision."""
    monthly_payment: MoneyField
    principal: MoneyField
    apr: RateField
    term_months: int
    total_interest: MoneyField
    total_cost: MoneyField
    rule_id: str
    lender_name: str
    ltv: RateField
    doc_fee: MoneyField
    days_basis: str = "30/360"


class PennyPerfectResult(BaseModel):
    """Result of penny-perfect verification."""
    is_match: bool = Field(description="True if within $0.01 tolerance")
    calculated: MoneyField
    expected: MoneyField
    difference: MoneyField
    tolerance: MoneyField = Field(default=Decimal("0.01"))


class DayCountComparison(BaseModel):
    """Comparison of payments using different day-count methods."""
    principal: MoneyField
    apr: RateField
    term_months: int
    thirty_360_payment: MoneyField
    actual_365_payment: MoneyField
    bank_365_360_payment: MoneyField
    max_difference: MoneyField


# Factory functions

def create_payment_estimate(
    monthly_payment: Decimal,
    principal: Decimal,
    apr: Decimal,
    term_months: int,
    rule_id: str,
    lender_name: str,
    ltv: Decimal,
    doc_fee: Decimal,
    days_basis: str = "30/360"
) -> PaymentEstimate:
    """Create a payment estimate with calculated totals."""
    total_of_payments = monthly_payment * term_months
    total_interest = total_of_payments - principal + doc_fee

    return PaymentEstimate(
        monthly_payment=monthly_payment,
        principal=principal,
        apr=apr,
        term_months=term_months,
        total_interest=total_interest,
        total_cost=total_of_payments + doc_fee,
        rule_id=rule_id,
        lender_name=lender_name,
        ltv=ltv,
        doc_fee=doc_fee,
        days_basis=days_basis
    )


def verify_penny_perfect(
    calculated: Decimal,
    expected: Decimal,
    tolerance: Decimal = Decimal("0.01")
) -> PennyPerfectResult:
    """Verify calculation matches expected within tolerance."""
    calculated = validate_money(calculated)
    expected = validate_money(expected)
    difference = abs(calculated - expected)

    return PennyPerfectResult(
        is_match=difference <= tolerance,
        calculated=calculated,
        expected=expected,
        difference=difference,
        tolerance=tolerance
    )
