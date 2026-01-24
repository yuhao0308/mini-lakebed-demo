"""
Payment Calculator Service

This module provides DETERMINISTIC payment calculations.
The LLM must NEVER generate payment amounts - only this module calculates them.

All calculations use the standard amortizing loan formula and cite rule IDs.

T04: Upgraded to use Decimal precision for penny-perfect calculations.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union
from app.services.database import execute_one, execute_query
from app.services.day_count import (
    DayCountMethod,
    calculate_monthly_payment as dc_calculate_monthly_payment,
    to_decimal,
    round_money
)


@dataclass
class PaymentResult:
    """Result of a payment calculation with full audit trail."""
    monthly_payment: float
    principal: float
    apr: float
    term_months: int
    total_interest: float
    total_cost: float
    rule_id: str
    lender_name: str
    ltv: float
    doc_fee: float
    days_basis: str = "30/360"  # T04: Day count method used


def calculate_monthly_payment(
    principal: Union[float, Decimal],
    apr: Union[float, Decimal],
    term_months: int,
    method: DayCountMethod = DayCountMethod.THIRTY_360
) -> float:
    """
    Calculate monthly payment using standard amortization formula.

    T04: Now uses Decimal precision internally via day_count module.

    Formula: P × [r(1+r)^n] / [(1+r)^n – 1]

    Where:
        P = Principal (loan amount)
        r = Monthly interest rate (APR / 12 / 100)
        n = Number of months (term)

    Args:
        principal: Loan amount
        apr: Annual percentage rate
        term_months: Loan term in months
        method: Day count convention (default 30/360 for consumer loans)

    Returns:
        Monthly payment amount rounded to 2 decimal places (as float for backward compatibility)
    """
    if principal <= 0:
        raise ValueError("Principal must be positive")
    if term_months <= 0:
        raise ValueError("Term must be positive")

    # Use Decimal-based calculation from day_count module
    payment = dc_calculate_monthly_payment(
        principal=to_decimal(principal),
        annual_rate=to_decimal(apr),
        term_months=term_months,
        method=method
    )

    # Return as float for backward compatibility
    return float(payment)


async def select_lender_rule(
    fico_score: int,
    term_months: int,
    ltv: float
) -> Optional[dict]:
    """
    Select the best matching lender rule based on criteria.
    
    Priority: Lowest APR among matching rules.
    
    Args:
        fico_score: Customer's estimated FICO score
        term_months: Desired loan term in months
        ltv: Loan-to-value ratio (principal / vehicle_price)
    
    Returns:
        Matching rule dict or None if no rule matches
    """
    query = """
        SELECT * FROM lender_rules
        WHERE ? BETWEEN min_fico AND max_fico
          AND ? BETWEEN min_term_months AND max_term_months
          AND ? <= max_ltv
          AND is_demo = 1
          AND (expiration_date IS NULL OR expiration_date >= DATE('now'))
        ORDER BY base_apr ASC
        LIMIT 1
    """
    
    return await execute_one(query, (fico_score, term_months, ltv))


async def estimate_payment(
    vehicle_price: float,
    down_payment: float,
    fico_score: int,
    term_months: int,
    doc_fee_override: Optional[float] = None
) -> Optional[PaymentResult]:
    """
    Calculate a payment estimate using approved lender rules.

    This is the main entry point for payment calculations.

    T04: Now uses Decimal precision and supports day count methods.

    Args:
        vehicle_price: Vehicle sale price
        down_payment: Customer down payment amount
        fico_score: Estimated FICO score
        term_months: Desired loan term
        doc_fee_override: Optional override for doc fee

    Returns:
        PaymentResult with full calculation details, or None if no matching rule
    """
    # Calculate LTV
    if vehicle_price <= 0:
        raise ValueError("Vehicle price must be positive")

    loan_amount = vehicle_price - down_payment
    if loan_amount <= 0:
        raise ValueError("Loan amount must be positive (reduce down payment)")

    ltv = loan_amount / vehicle_price

    # Find matching rule
    rule = await select_lender_rule(fico_score, term_months, ltv)

    if not rule:
        return None

    # Apply doc fee
    doc_fee = doc_fee_override if doc_fee_override is not None else (rule["doc_fee"] or 0)
    principal = loan_amount + doc_fee

    # Validate loan amount against rule limits
    if principal < rule["min_loan_amount"]:
        raise ValueError(f"Loan amount ${principal:.2f} below minimum ${rule['min_loan_amount']:.2f}")
    if principal > rule["max_loan_amount"]:
        raise ValueError(f"Loan amount ${principal:.2f} exceeds maximum ${rule['max_loan_amount']:.2f}")

    # Get day count method from rule (T04)
    days_basis_str = rule.get("days_basis", "30/360")
    try:
        days_basis = DayCountMethod(days_basis_str)
    except ValueError:
        days_basis = DayCountMethod.THIRTY_360

    # Calculate payment using Decimal precision (T04)
    apr = rule["base_apr"]
    monthly_payment = calculate_monthly_payment(principal, apr, term_months, method=days_basis)

    # Calculate totals
    total_paid = monthly_payment * term_months + down_payment
    total_interest = total_paid - vehicle_price - doc_fee

    return PaymentResult(
        monthly_payment=monthly_payment,
        principal=principal,
        apr=apr,
        term_months=term_months,
        total_interest=round(total_interest, 2),
        total_cost=round(total_paid, 2),
        rule_id=rule["rule_id"],
        lender_name=rule["lender_name"],
        ltv=round(ltv, 3),
        doc_fee=doc_fee,
        days_basis=days_basis.value
    )


def verify_llm_payment(
    llm_stated_payment: float,
    calculated_payment: float,
    tolerance: float = 0.01
) -> bool:
    """
    Verify that LLM-stated payment matches calculated value.
    
    This is a guardrail to prevent LLM hallucination of payment amounts.
    If this returns False, the system should use calculated_payment.
    
    Args:
        llm_stated_payment: Payment amount from LLM response
        calculated_payment: Payment from deterministic calculation
        tolerance: Allowed relative difference (default 1%)
    
    Returns:
        True if payments match within tolerance
    """
    if calculated_payment == 0:
        return llm_stated_payment == 0
    
    relative_diff = abs(llm_stated_payment - calculated_payment) / calculated_payment
    return relative_diff <= tolerance
