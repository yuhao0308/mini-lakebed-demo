"""
T04: Tax Calculator Service

State-specific tax calculation with trade-in credit rules.
Per tasks/T04_math_precision.md and 03_implementation_dummy_data_plan.md §4.2

Critical difference by state:
- CA, MI, VA: Tax on full vehicle price (trade-in does NOT reduce taxable basis)
- AZ, NV, TX, FL: Trade-in value reduces taxable basis

Example from spec:
- $50k car, $40k trade-in, 8% tax rate
- CA: Tax = $50,000 × 0.08 = $4,000
- AZ: Tax = ($50,000 - $40,000) × 0.08 = $800
- Difference: $3,200
"""

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

from app.services.database import execute_one, execute_query

logger = logging.getLogger(__name__)

# Precision constants
CENTS = Decimal("0.01")
RATE_PRECISION = Decimal("0.0001")  # 4 decimal places for rates


def to_decimal(value) -> Decimal:
    """Convert a value to Decimal with proper handling."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def round_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places using banker's rounding."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def round_rate(value: Decimal) -> Decimal:
    """Round rate to 4 decimal places."""
    return value.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)


class TaxBasisRule(str, Enum):
    """
    State-specific tax basis calculation rules.

    Ref: 03_implementation_dummy_data_plan.md §4.2
    """
    FULL_PRICE = "FULL_PRICE"            # CA, MI, VA - Trade-in does NOT reduce tax
    TRADE_IN_CREDIT = "TRADE_IN_CREDIT"  # AZ, NV, TX, FL - Trade-in reduces taxable basis


# States by tax basis rule
FULL_PRICE_STATES = {"CA", "MI", "VA"}
TRADE_IN_CREDIT_STATES = {"AZ", "NV", "TX", "FL"}


@dataclass
class TaxJurisdiction:
    """Tax rates and rules for a specific location."""
    zip_code: str
    state: str
    city: str
    county: str
    state_rate: Decimal
    county_rate: Decimal
    city_rate: Decimal
    special_district_rate: Decimal
    combined_rate: Decimal
    tax_basis_rule: TaxBasisRule
    trade_in_credit: bool


@dataclass
class TaxCalculation:
    """Complete tax calculation with audit trail."""
    jurisdiction: TaxJurisdiction
    selling_price: Decimal
    taxable_fees: Decimal
    trade_in_allowance: Decimal
    taxable_basis: Decimal
    tax_amount: Decimal
    rule_applied: str  # Human-readable explanation


class TaxCalculator:
    """
    State-specific tax calculation engine.

    Critical: CA taxes the full vehicle price regardless of trade-in.
    AZ/NV/TX/FL allow trade-in value to reduce taxable basis.

    Example from spec:
    - $50k car, $40k trade-in
    - CA (8%): Tax = $50,000 × 0.08 = $4,000
    - AZ (8%): Tax = ($50,000 - $40,000) × 0.08 = $800
    - Difference: $3,200
    """

    async def get_jurisdiction(self, zip_code: str) -> TaxJurisdiction:
        """
        Load tax jurisdiction from reference data.

        Args:
            zip_code: 5-digit ZIP code

        Returns:
            TaxJurisdiction with rates and rules

        Raises:
            ValueError: If ZIP code not found in reference data
        """
        # Query tax_rates table
        row = await execute_one(
            """
            SELECT zip_code, state, city, county,
                   state_rate, county_rate, city_rate,
                   special_district_rate, combined_rate,
                   tax_basis_rule, trade_in_credit
            FROM tax_rates
            WHERE zip_code = ?
            """,
            (zip_code,)
        )

        if not row:
            raise ValueError(f"Unknown tax jurisdiction for ZIP code: {zip_code}")

        # Determine tax basis rule from state
        state = row["state"]
        if state in FULL_PRICE_STATES:
            tax_basis_rule = TaxBasisRule.FULL_PRICE
            trade_in_credit = False
        elif state in TRADE_IN_CREDIT_STATES:
            tax_basis_rule = TaxBasisRule.TRADE_IN_CREDIT
            trade_in_credit = True
        else:
            # Default to database value or trade-in credit
            tax_basis_rule = TaxBasisRule(row.get("tax_basis_rule", "TRADE_IN_CREDIT"))
            trade_in_credit = row.get("trade_in_credit", True)

        return TaxJurisdiction(
            zip_code=row["zip_code"],
            state=state,
            city=row["city"],
            county=row["county"],
            state_rate=round_rate(to_decimal(row["state_rate"])),
            county_rate=round_rate(to_decimal(row["county_rate"])),
            city_rate=round_rate(to_decimal(row["city_rate"])),
            special_district_rate=round_rate(to_decimal(row.get("special_district_rate", 0))),
            combined_rate=round_rate(to_decimal(row["combined_rate"])),
            tax_basis_rule=tax_basis_rule,
            trade_in_credit=trade_in_credit
        )

    def calculate_taxable_basis(
        self,
        selling_price: Decimal,
        taxable_fees: Decimal,
        trade_in_allowance: Decimal,
        jurisdiction: TaxJurisdiction
    ) -> Decimal:
        """
        Calculate taxable basis based on state rules.

        If state in [CA, MI, VA]:
            basis = selling_price + taxable_fees
        If state in [AZ, NV, TX, FL]:
            basis = (selling_price + taxable_fees) - trade_in_allowance

        Args:
            selling_price: Vehicle selling price
            taxable_fees: Fees subject to tax (varies by state)
            trade_in_allowance: Trade-in value offered
            jurisdiction: Tax jurisdiction with rules

        Returns:
            Taxable basis amount
        """
        selling_price = to_decimal(selling_price)
        taxable_fees = to_decimal(taxable_fees)
        trade_in_allowance = to_decimal(trade_in_allowance)

        base_amount = selling_price + taxable_fees

        if jurisdiction.tax_basis_rule == TaxBasisRule.FULL_PRICE:
            # CA/MI/VA: No trade-in credit
            return round_money(base_amount)
        else:
            # AZ/NV/TX/FL: Trade-in reduces taxable basis
            basis = base_amount - trade_in_allowance
            # Cannot have negative taxable basis
            return round_money(max(basis, Decimal("0")))

    async def calculate_tax(
        self,
        selling_price: Decimal,
        taxable_fees: Decimal,
        trade_in_allowance: Decimal,
        zip_code: str
    ) -> TaxCalculation:
        """
        Full tax calculation with jurisdiction lookup and rule application.

        Args:
            selling_price: Vehicle selling price
            taxable_fees: Fees subject to tax
            trade_in_allowance: Trade-in value offered
            zip_code: Customer's ZIP code

        Returns:
            TaxCalculation with full audit trail
        """
        selling_price = to_decimal(selling_price)
        taxable_fees = to_decimal(taxable_fees)
        trade_in_allowance = to_decimal(trade_in_allowance)

        # Get jurisdiction
        jurisdiction = await self.get_jurisdiction(zip_code)

        # Calculate taxable basis
        taxable_basis = self.calculate_taxable_basis(
            selling_price, taxable_fees, trade_in_allowance, jurisdiction
        )

        # Calculate tax
        # Combined rate is stored as decimal (e.g., 0.0775 for 7.75%)
        tax_amount = round_money(taxable_basis * jurisdiction.combined_rate)

        # Build rule explanation
        rate_percent = jurisdiction.combined_rate * Decimal("100")
        if jurisdiction.tax_basis_rule == TaxBasisRule.FULL_PRICE:
            rule_applied = (
                f"{jurisdiction.state} taxes full vehicle price regardless of trade-in. "
                f"Taxable basis: ${selling_price:,.2f} + ${taxable_fees:,.2f} fees = ${taxable_basis:,.2f}. "
                f"Tax: ${taxable_basis:,.2f} × {rate_percent:.2f}% = ${tax_amount:,.2f}"
            )
        else:
            rule_applied = (
                f"{jurisdiction.state} allows trade-in credit. "
                f"Taxable basis: ${selling_price:,.2f} + ${taxable_fees:,.2f} fees - ${trade_in_allowance:,.2f} trade-in = ${taxable_basis:,.2f}. "
                f"Tax: ${taxable_basis:,.2f} × {rate_percent:.2f}% = ${tax_amount:,.2f}"
            )

        return TaxCalculation(
            jurisdiction=jurisdiction,
            selling_price=selling_price,
            taxable_fees=taxable_fees,
            trade_in_allowance=trade_in_allowance,
            taxable_basis=taxable_basis,
            tax_amount=tax_amount,
            rule_applied=rule_applied
        )

    def compare_tax_by_state(
        self,
        selling_price: Decimal,
        taxable_fees: Decimal,
        trade_in_allowance: Decimal,
        combined_rate: Decimal
    ) -> dict:
        """
        Compare tax amount between full-price and trade-in-credit states.

        Useful for demonstrating the $3,200 difference from spec.

        Args:
            selling_price: Vehicle selling price
            taxable_fees: Fees subject to tax
            trade_in_allowance: Trade-in value offered
            combined_rate: Tax rate as percentage (e.g., 8.0 for 8%)

        Returns:
            Dict with full_price_tax, trade_in_credit_tax, difference
        """
        selling_price = to_decimal(selling_price)
        taxable_fees = to_decimal(taxable_fees)
        trade_in_allowance = to_decimal(trade_in_allowance)
        combined_rate = to_decimal(combined_rate)

        tax_rate = combined_rate / Decimal("100")

        # Full price basis (CA/MI/VA)
        full_price_basis = selling_price + taxable_fees
        full_price_tax = round_money(full_price_basis * tax_rate)

        # Trade-in credit basis (AZ/NV/TX/FL)
        trade_in_basis = max(full_price_basis - trade_in_allowance, Decimal("0"))
        trade_in_credit_tax = round_money(trade_in_basis * tax_rate)

        difference = round_money(full_price_tax - trade_in_credit_tax)

        return {
            "full_price_basis": full_price_basis,
            "full_price_tax": full_price_tax,
            "trade_in_credit_basis": trade_in_basis,
            "trade_in_credit_tax": trade_in_credit_tax,
            "difference": difference,
            "rate_applied": combined_rate
        }


# Module-level convenience functions

async def get_tax_jurisdiction(zip_code: str) -> TaxJurisdiction:
    """Get tax jurisdiction for a ZIP code."""
    calculator = TaxCalculator()
    return await calculator.get_jurisdiction(zip_code)


async def calculate_sales_tax(
    selling_price: Decimal,
    taxable_fees: Decimal,
    trade_in_allowance: Decimal,
    zip_code: str
) -> TaxCalculation:
    """Calculate sales tax for a vehicle purchase."""
    calculator = TaxCalculator()
    return await calculator.calculate_tax(
        selling_price, taxable_fees, trade_in_allowance, zip_code
    )


def compare_state_tax_rules(
    selling_price: Decimal,
    taxable_fees: Decimal,
    trade_in_allowance: Decimal,
    tax_rate: Decimal
) -> dict:
    """Compare tax between full-price and trade-in-credit states."""
    calculator = TaxCalculator()
    return calculator.compare_tax_by_state(
        selling_price, taxable_fees, trade_in_allowance, tax_rate
    )
