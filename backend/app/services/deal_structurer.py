"""
T04: Deal Structurer Service

The Fin_Calc_Solver implementation - orchestrates penny-perfect deal calculations.
Per tasks/T04_math_precision.md

Steps (per spec §2.3):
1. Tax Determination - state-specific rules
2. Fee Injection - mandatory state fees
3. Lender Matching - best rate for tier/LTV
4. Amortization - using lender's day-count method
"""

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional
import uuid
from datetime import datetime
import logging

from app.services.database import execute_one, execute_query
from app.services.day_count import (
    DayCountMethod,
    calculate_monthly_payment,
    calculate_total_of_payments,
    calculate_finance_charge,
    to_decimal,
    round_money,
    verify_penny_perfect
)
from app.services.tax_calculator import TaxCalculator, TaxCalculation
from app.models.financial import (
    TradeInDetails,
    FeeBreakdown,
    TaxBreakdown,
    LendingTerms,
    DealSummary
)

logger = logging.getLogger(__name__)

# Constants
CENTS = Decimal("0.01")
DEFAULT_DOC_FEE = Decimal("85.00")
DEFAULT_LICENSE_FEE = Decimal("150.00")
DEFAULT_REGISTRATION_FEE = Decimal("75.00")


@dataclass
class DealStructure:
    """
    Complete deal structure with penny-perfect calculations.

    Per 03_implementation_dummy_data_plan.md §1.3
    """
    # Pricing
    selling_price: Decimal
    sb766_offering_price: Decimal
    rebates_total: Decimal

    # Down payment / Trade
    cash_down_payment: Decimal
    trade_in_allowance: Decimal
    trade_in_payoff: Decimal
    trade_in_equity: Decimal
    negative_equity_financed: Decimal

    # Tax
    tax_calculation: TaxCalculation

    # Fees
    doc_fee: Decimal
    license_fee: Decimal
    registration_fee: Decimal
    total_fees: Decimal

    # Lending
    lender_id: str
    lender_name: str
    program_tier: str
    term_months: int
    buy_rate: Decimal
    contract_apr: Decimal
    dealer_reserve: Decimal
    days_basis: DayCountMethod
    amount_financed: Decimal
    monthly_payment: Decimal
    total_of_payments: Decimal
    finance_charge: Decimal

    # Validation
    ltv: Decimal
    payment_packing_check: bool  # monthly × term == total_of_payments


class DealStructurer:
    """
    The Fin_Calc_Solver implementation.

    Orchestrates tax calculation, fee injection, lender matching,
    and amortization to produce penny-perfect deal structures.
    """

    def __init__(self):
        self.tax_calculator = TaxCalculator()

    async def structure_deal(
        self,
        vehicle_id: int,
        customer_zip: str,
        fico_score: int,
        down_payment: Decimal,
        trade_in: Optional[TradeInDetails] = None,
        requested_term: int = 60,
        dealer_reserve: Decimal = Decimal("0")
    ) -> Optional[DealStructure]:
        """
        Build complete deal structure.

        Steps (per spec §2.3):
        1. Tax Determination - state-specific rules
        2. Fee Injection - mandatory state fees
        3. Lender Matching - best rate for tier/LTV
        4. Amortization - using lender's day-count method

        Args:
            vehicle_id: Vehicle inventory ID
            customer_zip: Customer ZIP code for tax jurisdiction
            fico_score: Customer's FICO score
            down_payment: Cash down payment amount
            trade_in: Optional trade-in details
            requested_term: Loan term in months
            dealer_reserve: Dealer markup on rate

        Returns:
            DealStructure with penny-perfect calculations, or None if no matching lender
        """
        down_payment = to_decimal(down_payment)
        dealer_reserve = to_decimal(dealer_reserve)

        # Get vehicle
        vehicle = await execute_one(
            "SELECT * FROM inventory WHERE id = ?",
            (vehicle_id,)
        )
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        selling_price = to_decimal(vehicle["price"])
        sb766_offering_price = to_decimal(vehicle.get("sb766_offering_price") or vehicle["price"])

        # Process trade-in
        trade_in_allowance = Decimal("0")
        trade_in_payoff = Decimal("0")
        trade_in_equity = Decimal("0")
        negative_equity = Decimal("0")

        if trade_in and trade_in.has_trade:
            trade_in_allowance = to_decimal(trade_in.allowance)
            trade_in_payoff = to_decimal(trade_in.payoff_amount)
            equity = trade_in_allowance - trade_in_payoff
            if equity >= 0:
                trade_in_equity = equity
            else:
                negative_equity = abs(equity)

        # Step 1: Tax Determination
        # Standard fees (could be made configurable per state)
        doc_fee = DEFAULT_DOC_FEE
        license_fee = DEFAULT_LICENSE_FEE
        registration_fee = DEFAULT_REGISTRATION_FEE
        total_fees = doc_fee + license_fee + registration_fee

        # Calculate tax (taxable fees typically include doc fee only)
        taxable_fees = doc_fee
        tax_calculation = await self.tax_calculator.calculate_tax(
            selling_price=selling_price,
            taxable_fees=taxable_fees,
            trade_in_allowance=trade_in_allowance,
            zip_code=customer_zip
        )

        # Step 2: Calculate Amount Financed
        # Amount financed = selling_price - down_payment - trade_in_equity + negative_equity + taxes + fees
        total_due = selling_price + tax_calculation.tax_amount + total_fees
        total_down = down_payment + trade_in_equity
        amount_financed = total_due - total_down + negative_equity

        amount_financed = round_money(amount_financed)

        # Validate amount financed is positive
        if amount_financed <= 0:
            raise ValueError("Amount financed must be positive")

        # Calculate LTV
        ltv = amount_financed / selling_price

        # Step 3: Lender Matching
        rule = await self._select_lender_rule(fico_score, requested_term, ltv)
        if not rule:
            return None

        # Parse day count method from rule
        days_basis_str = rule.get("days_basis", "30/360")
        try:
            days_basis = DayCountMethod(days_basis_str)
        except ValueError:
            days_basis = DayCountMethod.THIRTY_360

        buy_rate = to_decimal(rule["base_apr"])
        contract_apr = buy_rate + dealer_reserve

        # Step 4: Amortization
        monthly_payment = calculate_monthly_payment(
            principal=amount_financed,
            annual_rate=contract_apr,
            term_months=requested_term,
            method=days_basis
        )

        total_of_payments = calculate_total_of_payments(monthly_payment, requested_term)
        finance_charge = calculate_finance_charge(total_of_payments, amount_financed)

        # Payment packing check: monthly × term == total_of_payments
        payment_packing_check = self.validate_payment_packing(
            monthly_payment, requested_term, total_of_payments
        )

        return DealStructure(
            selling_price=selling_price,
            sb766_offering_price=sb766_offering_price,
            rebates_total=Decimal("0"),
            cash_down_payment=down_payment,
            trade_in_allowance=trade_in_allowance,
            trade_in_payoff=trade_in_payoff,
            trade_in_equity=trade_in_equity,
            negative_equity_financed=negative_equity,
            tax_calculation=tax_calculation,
            doc_fee=doc_fee,
            license_fee=license_fee,
            registration_fee=registration_fee,
            total_fees=total_fees,
            lender_id=rule["rule_id"],
            lender_name=rule["lender_name"],
            program_tier=rule["credit_tier"],
            term_months=requested_term,
            buy_rate=buy_rate,
            contract_apr=contract_apr,
            dealer_reserve=dealer_reserve,
            days_basis=days_basis,
            amount_financed=amount_financed,
            monthly_payment=monthly_payment,
            total_of_payments=total_of_payments,
            finance_charge=finance_charge,
            ltv=round_money(ltv * 100) / 100,  # Round LTV to 2 decimal places
            payment_packing_check=payment_packing_check
        )

    async def _select_lender_rule(
        self,
        fico_score: int,
        term_months: int,
        ltv: Decimal
    ) -> Optional[dict]:
        """
        Select the best matching lender rule based on criteria.

        Priority: Lowest APR among matching rules.
        """
        ltv_float = float(ltv)
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
        return await execute_one(query, (fico_score, term_months, ltv_float))

    def validate_payment_packing(
        self,
        monthly_payment: Decimal,
        term_months: int,
        total_of_payments: Decimal
    ) -> bool:
        """
        Verify no hidden fees: monthly × term == total_of_payments

        Per spec §6.1: Any deviation suggests hidden fees.
        """
        expected_total = round_money(to_decimal(monthly_payment) * Decimal(str(term_months)))
        return verify_penny_perfect(expected_total, total_of_payments)

    def validate_ltv(
        self,
        deal: DealStructure,
        max_ltv: Decimal
    ) -> bool:
        """Verify LTV within lender constraints."""
        return deal.ltv <= to_decimal(max_ltv)

    def to_deal_summary(self, deal: DealStructure, vehicle_id: int) -> DealSummary:
        """Convert DealStructure to DealSummary Pydantic model."""
        tax_breakdown = TaxBreakdown(
            jurisdiction_code=deal.tax_calculation.jurisdiction.zip_code,
            state=deal.tax_calculation.jurisdiction.state,
            tax_rate_combined=deal.tax_calculation.jurisdiction.combined_rate,
            taxable_basis=deal.tax_calculation.taxable_basis,
            total_sales_tax=deal.tax_calculation.tax_amount,
            rule_applied=deal.tax_calculation.rule_applied,
            trade_in_credit_applied=(deal.tax_calculation.jurisdiction.trade_in_credit and deal.trade_in_allowance > 0)
        )

        fee_breakdown = FeeBreakdown(
            doc_fee=deal.doc_fee,
            license_fee=deal.license_fee,
            registration_fee=deal.registration_fee,
            total_fees=deal.total_fees
        )

        lending_terms = LendingTerms(
            lender_id=deal.lender_id,
            lender_name=deal.lender_name,
            program_tier=deal.program_tier,
            term_months=deal.term_months,
            buy_rate=deal.buy_rate,
            contract_apr=deal.contract_apr,
            dealer_reserve=deal.dealer_reserve,
            days_basis=deal.days_basis.value,
            amount_financed=deal.amount_financed,
            monthly_payment=deal.monthly_payment,
            total_of_payments=deal.total_of_payments,
            finance_charge=deal.finance_charge
        )

        trade_in = None
        if deal.trade_in_allowance > 0:
            trade_in = TradeInDetails(
                has_trade=True,
                allowance=deal.trade_in_allowance,
                payoff_amount=deal.trade_in_payoff,
                equity_amount=deal.trade_in_equity,
                negative_equity_financed=deal.negative_equity_financed
            )

        return DealSummary(
            deal_id=str(uuid.uuid4()),
            vehicle_id=vehicle_id,
            created_at=datetime.utcnow(),
            selling_price=deal.selling_price,
            sb766_offering_price=deal.sb766_offering_price,
            rebates_total=deal.rebates_total,
            cash_down_payment=deal.cash_down_payment,
            trade_in=trade_in,
            tax=tax_breakdown,
            fees=fee_breakdown,
            lending=lending_terms,
            ltv=deal.ltv,
            payment_packing_verified=deal.payment_packing_check
        )


# Module-level convenience functions

async def structure_deal(
    vehicle_id: int,
    customer_zip: str,
    fico_score: int,
    down_payment: Decimal,
    trade_in: Optional[TradeInDetails] = None,
    requested_term: int = 60
) -> Optional[DealStructure]:
    """Structure a complete deal with penny-perfect calculations."""
    structurer = DealStructurer()
    return await structurer.structure_deal(
        vehicle_id=vehicle_id,
        customer_zip=customer_zip,
        fico_score=fico_score,
        down_payment=down_payment,
        trade_in=trade_in,
        requested_term=requested_term
    )


def validate_deal_payment_packing(deal: DealStructure) -> bool:
    """Verify no payment packing in a deal."""
    structurer = DealStructurer()
    return structurer.validate_payment_packing(
        deal.monthly_payment, deal.term_months, deal.total_of_payments
    )
