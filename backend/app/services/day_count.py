"""
T04: Day Count Methods for Interest Calculation

Implements all three day-count conventions for penny-perfect calculations:
- 30/360: Standard consumer loans
- Actual/365: Simple interest with daily accrual
- 365/360: Bank method (higher effective rate)

Per tasks/T04_math_precision.md and 03_implementation_dummy_data_plan.md §4.1
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import logging

# Set high precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)


class DayCountMethod(str, Enum):
    """
    Interest calculation day-count conventions.

    Ref: 03_implementation_dummy_data_plan.md §4.1
    """
    THIRTY_360 = "30/360"       # Standard consumer loans
    ACTUAL_365 = "actual/365"   # Simple interest with daily accrual
    BANK_365_360 = "365/360"    # Bank method (higher effective rate)


@dataclass
class InterestCalculation:
    """Result of interest calculation with audit trail."""
    principal: Decimal
    annual_rate: Decimal
    method: DayCountMethod
    period_interest: Decimal
    daily_rate: Decimal
    days_in_period: int


# Constants for calculations
DAYS_IN_YEAR_360 = Decimal("360")
DAYS_IN_YEAR_365 = Decimal("365")
MONTHS_IN_YEAR = Decimal("12")
CENTS = Decimal("0.01")
RATE_PRECISION = Decimal("0.000001")  # 6 decimal places for rates


def to_decimal(value) -> Decimal:
    """Convert a value to Decimal with proper handling."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places using banker's rounding (ROUND_HALF_UP)."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def round_rate(value: Decimal) -> Decimal:
    """Round rate to 6 decimal places."""
    return value.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)


def calculate_monthly_rate(
    annual_rate: Decimal,
    method: DayCountMethod,
    round_result: bool = True
) -> Decimal:
    """
    Calculate the monthly interest rate based on day-count method.

    30/360: rate / 12 (simple division)
    Actual/365: rate / 365 * 30 (average month)
    365/360: rate / 360 * 30 (effectively higher)

    Args:
        annual_rate: Annual percentage rate (e.g., 5.0 for 5%)
        method: Day count convention
        round_result: Whether to round the result (default True for backward compat)

    Returns:
        Monthly rate as decimal (e.g., 0.004167 for 5% using 30/360)
    """
    annual_rate = to_decimal(annual_rate)
    rate_decimal = annual_rate / Decimal("100")  # Convert percentage to decimal

    if method == DayCountMethod.THIRTY_360:
        # Standard: simple division by 12
        monthly_rate = rate_decimal / MONTHS_IN_YEAR
    elif method == DayCountMethod.ACTUAL_365:
        # Daily rate * 30 days (average month)
        daily_rate = rate_decimal / DAYS_IN_YEAR_365
        monthly_rate = daily_rate * Decimal("30")
    elif method == DayCountMethod.BANK_365_360:
        # Bank method: uses 360-day year (increases effective rate)
        daily_rate = rate_decimal / DAYS_IN_YEAR_360
        monthly_rate = daily_rate * Decimal("30")
    else:
        raise ValueError(f"Unknown day count method: {method}")

    return round_rate(monthly_rate) if round_result else monthly_rate


def calculate_daily_rate(
    annual_rate: Decimal,
    method: DayCountMethod
) -> Decimal:
    """
    Calculate daily interest rate based on day-count method.

    Args:
        annual_rate: Annual percentage rate
        method: Day count convention

    Returns:
        Daily rate as decimal
    """
    annual_rate = to_decimal(annual_rate)
    rate_decimal = annual_rate / Decimal("100")

    if method == DayCountMethod.THIRTY_360:
        # 30/360: 1/360 of annual rate
        daily_rate = rate_decimal / DAYS_IN_YEAR_360
    elif method == DayCountMethod.ACTUAL_365:
        # Actual/365: 1/365 of annual rate
        daily_rate = rate_decimal / DAYS_IN_YEAR_365
    elif method == DayCountMethod.BANK_365_360:
        # Bank: 1/360 of annual rate (same as 30/360 daily)
        daily_rate = rate_decimal / DAYS_IN_YEAR_360
    else:
        raise ValueError(f"Unknown day count method: {method}")

    return round_rate(daily_rate)


def calculate_period_interest(
    principal: Decimal,
    annual_rate: Decimal,
    method: DayCountMethod,
    days_in_period: int = 30
) -> InterestCalculation:
    """
    Calculate interest for a period using specified day-count method.

    30/360 Method:
        I = P × R × (30/360) = P × R / 12
        Assumes 30-day months and 360-day years

    Actual/365 Method:
        I = P × R × (d/365)
        where d = actual days in period

    365/360 Method (Bank):
        I = P × R × (d/360)
        Effectively increases rate by 365/360 ≈ 1.39%

    Args:
        principal: Loan balance
        annual_rate: Annual percentage rate
        method: Day count convention
        days_in_period: Number of days in the period

    Returns:
        InterestCalculation with full audit trail
    """
    principal = to_decimal(principal)
    annual_rate = to_decimal(annual_rate)
    rate_decimal = annual_rate / Decimal("100")
    days = Decimal(str(days_in_period))

    daily_rate = calculate_daily_rate(annual_rate, method)

    if method == DayCountMethod.THIRTY_360:
        # 30/360: P × R / 12 (uses 30-day month regardless of actual)
        period_interest = principal * rate_decimal / MONTHS_IN_YEAR
    elif method == DayCountMethod.ACTUAL_365:
        # Actual/365: P × R × (days / 365)
        period_interest = principal * rate_decimal * (days / DAYS_IN_YEAR_365)
    elif method == DayCountMethod.BANK_365_360:
        # 365/360: P × R × (days / 360)
        period_interest = principal * rate_decimal * (days / DAYS_IN_YEAR_360)
        # Log warning for consumer loans using bank method
        logger.warning(
            f"365/360 method used for consumer calculation - "
            f"effective rate increased by ~{((DAYS_IN_YEAR_365 / DAYS_IN_YEAR_360) - 1) * 100:.2f}%"
        )
    else:
        raise ValueError(f"Unknown day count method: {method}")

    return InterestCalculation(
        principal=principal,
        annual_rate=annual_rate,
        method=method,
        period_interest=round_money(period_interest),
        daily_rate=daily_rate,
        days_in_period=days_in_period
    )


def calculate_monthly_payment(
    principal: Decimal,
    annual_rate: Decimal,
    term_months: int,
    method: DayCountMethod = DayCountMethod.THIRTY_360
) -> Decimal:
    """
    Calculate monthly payment using amortization formula.

    Formula: P × [r(1+r)^n] / [(1+r)^n – 1]

    Where:
        P = Principal (loan amount)
        r = Monthly interest rate
        n = Number of months (term)

    Uses Decimal for arbitrary precision.
    Rounds to 2 decimal places using ROUND_HALF_UP (banker's rounding).

    Args:
        principal: Loan amount
        annual_rate: Annual percentage rate (e.g., 5.0 for 5%)
        term_months: Loan term in months
        method: Day count convention (default 30/360 for consumer loans)

    Returns:
        Monthly payment as Decimal rounded to 2 decimal places
    """
    principal = to_decimal(principal)
    annual_rate = to_decimal(annual_rate)

    if principal <= 0:
        raise ValueError("Principal must be positive")
    if term_months <= 0:
        raise ValueError("Term must be positive")

    # Zero interest case (special handling to avoid division by zero)
    if annual_rate == 0:
        payment = principal / Decimal(str(term_months))
        return round_money(payment)

    # Get monthly rate based on method - DON'T round to preserve full precision
    monthly_rate = calculate_monthly_rate(annual_rate, method, round_result=False)
    n = Decimal(str(term_months))

    # Standard amortization formula with Decimal precision
    # P × [r(1+r)^n] / [(1+r)^n – 1]
    one_plus_r = Decimal("1") + monthly_rate
    one_plus_r_n = one_plus_r ** n

    numerator = principal * monthly_rate * one_plus_r_n
    denominator = one_plus_r_n - Decimal("1")

    payment = numerator / denominator

    return round_money(payment)


def calculate_total_of_payments(
    monthly_payment: Decimal,
    term_months: int
) -> Decimal:
    """
    Calculate total of all payments over the loan term.

    Args:
        monthly_payment: Monthly payment amount
        term_months: Number of months

    Returns:
        Total of payments (monthly × term)
    """
    return round_money(to_decimal(monthly_payment) * Decimal(str(term_months)))


def calculate_finance_charge(
    total_of_payments: Decimal,
    amount_financed: Decimal
) -> Decimal:
    """
    Calculate finance charge (total interest paid).

    Args:
        total_of_payments: Sum of all payments
        amount_financed: Original loan amount

    Returns:
        Finance charge (total interest)
    """
    return round_money(to_decimal(total_of_payments) - to_decimal(amount_financed))


def verify_penny_perfect(
    calculated: Decimal,
    expected: Decimal,
    tolerance: Decimal = CENTS
) -> bool:
    """
    Verify calculation matches expected within penny tolerance.

    Per spec: Any variance > $0.01 is a build failure.

    Args:
        calculated: Calculated value
        expected: Expected value
        tolerance: Maximum allowed difference (default $0.01)

    Returns:
        True if within tolerance
    """
    calculated = to_decimal(calculated)
    expected = to_decimal(expected)
    tolerance = to_decimal(tolerance)

    diff = abs(calculated - expected)
    return diff <= tolerance


def get_effective_rate_increase(method: DayCountMethod) -> Decimal:
    """
    Get the effective rate increase factor for a day count method.

    365/360 increases effective rate by 365/360 ≈ 1.39%

    Args:
        method: Day count convention

    Returns:
        Multiplier for effective rate (1.0 for standard methods)
    """
    if method == DayCountMethod.BANK_365_360:
        return DAYS_IN_YEAR_365 / DAYS_IN_YEAR_360
    return Decimal("1")


def calculate_late_payment_interest(
    principal: Decimal,
    annual_rate: Decimal,
    method: DayCountMethod,
    days_late: int
) -> Decimal:
    """
    Calculate additional interest for late payment.

    Args:
        principal: Current loan balance
        annual_rate: Annual percentage rate
        method: Day count convention
        days_late: Number of days payment is late

    Returns:
        Additional interest accrued during late period
    """
    result = calculate_period_interest(
        principal=principal,
        annual_rate=annual_rate,
        method=method,
        days_in_period=days_late
    )
    return result.period_interest
