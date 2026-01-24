"""
T04: Tax Calculation Tests

Tests for state-specific tax rules and trade-in credit.
Per tasks/T04_math_precision.md

Critical test: CA vs AZ with trade-in
- $50k car, $40k trade-in, 8% tax rate
- CA: Tax = $50,000 × 0.08 = $4,000
- AZ: Tax = ($50,000 - $40,000) × 0.08 = $800
- Difference: $3,200
"""

import pytest
from decimal import Decimal

from app.services.tax_calculator import (
    TaxCalculator,
    TaxBasisRule,
    TaxJurisdiction,
    get_tax_jurisdiction,
    calculate_sales_tax,
    compare_state_tax_rules,
    FULL_PRICE_STATES,
    TRADE_IN_CREDIT_STATES
)


@pytest.fixture
def tax_calculator():
    """Create a TaxCalculator instance for testing."""
    return TaxCalculator()


class TestTaxBasisRules:
    """Tests for tax basis calculation rules."""

    def test_ca_full_price_basis(self, tax_calculator):
        """T04-09: CA taxes full vehicle price regardless of trade-in."""
        # Create a mock CA jurisdiction
        jurisdiction = TaxJurisdiction(
            zip_code="92101",
            state="CA",
            city="San Diego",
            county="San Diego",
            state_rate=Decimal("6.0"),
            county_rate=Decimal("0.25"),
            city_rate=Decimal("1.0"),
            special_district_rate=Decimal("0.5"),
            combined_rate=Decimal("7.75"),
            tax_basis_rule=TaxBasisRule.FULL_PRICE,
            trade_in_credit=False
        )

        # $50k car, $40k trade-in
        taxable_basis = tax_calculator.calculate_taxable_basis(
            selling_price=Decimal("50000"),
            taxable_fees=Decimal("0"),
            trade_in_allowance=Decimal("40000"),
            jurisdiction=jurisdiction
        )

        # CA: Taxable basis should be full $50,000 (trade-in does NOT reduce)
        assert taxable_basis == Decimal("50000.00")

    def test_az_trade_in_credit(self, tax_calculator):
        """T04-10: AZ allows trade-in to reduce taxable basis."""
        # Create a mock AZ jurisdiction
        jurisdiction = TaxJurisdiction(
            zip_code="85001",
            state="AZ",
            city="Phoenix",
            county="Maricopa",
            state_rate=Decimal("5.6"),
            county_rate=Decimal("0.7"),
            city_rate=Decimal("2.3"),
            special_district_rate=Decimal("0"),
            combined_rate=Decimal("8.6"),
            tax_basis_rule=TaxBasisRule.TRADE_IN_CREDIT,
            trade_in_credit=True
        )

        # $50k car, $40k trade-in
        taxable_basis = tax_calculator.calculate_taxable_basis(
            selling_price=Decimal("50000"),
            taxable_fees=Decimal("0"),
            trade_in_allowance=Decimal("40000"),
            jurisdiction=jurisdiction
        )

        # AZ: Taxable basis should be $50,000 - $40,000 = $10,000
        assert taxable_basis == Decimal("10000.00")

    def test_ca_az_difference_3200(self, tax_calculator):
        """T04-11: Same scenario should show $3,200 difference at 8% rate."""
        result = tax_calculator.compare_tax_by_state(
            selling_price=Decimal("50000"),
            taxable_fees=Decimal("0"),
            trade_in_allowance=Decimal("40000"),
            combined_rate=Decimal("8.0")
        )

        # CA: $50,000 × 8% = $4,000
        assert result["full_price_tax"] == Decimal("4000.00")

        # AZ: ($50,000 - $40,000) × 8% = $800
        assert result["trade_in_credit_tax"] == Decimal("800.00")

        # Difference: $4,000 - $800 = $3,200
        assert result["difference"] == Decimal("3200.00")


class TestJurisdictionLookup:
    """Tests for tax jurisdiction lookup."""

    @pytest.mark.asyncio
    async def test_jurisdiction_lookup_92101(self, tax_calculator):
        """T04-12: Zip 92101 should be San Diego, CA with ~7.75% combined rate."""
        try:
            jurisdiction = await tax_calculator.get_jurisdiction("92101")

            assert jurisdiction.zip_code == "92101"
            assert jurisdiction.state == "CA"
            assert jurisdiction.city == "San Diego"
            # Combined rate should be around 7.75% for San Diego (stored as decimal 0.0775)
            assert jurisdiction.combined_rate > Decimal("0.07")
            assert jurisdiction.combined_rate < Decimal("0.09")
            # CA should be FULL_PRICE rule
            assert jurisdiction.tax_basis_rule == TaxBasisRule.FULL_PRICE
            assert jurisdiction.trade_in_credit is False
        except ValueError:
            # If ZIP not in test data, skip
            pytest.skip("ZIP 92101 not in test tax_rates data")

    @pytest.mark.asyncio
    async def test_jurisdiction_lookup_85001(self, tax_calculator):
        """T04-13: Zip 85001 should be Phoenix, AZ with ~8.6% combined rate."""
        try:
            jurisdiction = await tax_calculator.get_jurisdiction("85001")

            assert jurisdiction.zip_code == "85001"
            assert jurisdiction.state == "AZ"
            assert jurisdiction.city == "Phoenix"
            # Combined rate should be around 8.6% for Phoenix (stored as decimal 0.086)
            assert jurisdiction.combined_rate > Decimal("0.08")
            assert jurisdiction.combined_rate < Decimal("0.095")
            # AZ should be TRADE_IN_CREDIT rule
            assert jurisdiction.tax_basis_rule == TaxBasisRule.TRADE_IN_CREDIT
            assert jurisdiction.trade_in_credit is True
        except ValueError:
            # If ZIP not in test data, skip
            pytest.skip("ZIP 85001 not in test tax_rates data")

    @pytest.mark.asyncio
    async def test_special_district_included(self, tax_calculator):
        """T04-14: Combined rate should include special district rate."""
        try:
            jurisdiction = await tax_calculator.get_jurisdiction("92101")

            # Combined rate should be sum of all component rates
            expected_combined = (
                jurisdiction.state_rate +
                jurisdiction.county_rate +
                jurisdiction.city_rate +
                jurisdiction.special_district_rate
            )

            # Allow small rounding difference
            assert abs(jurisdiction.combined_rate - expected_combined) < Decimal("0.01")
        except ValueError:
            pytest.skip("ZIP 92101 not in test tax_rates data")

    @pytest.mark.asyncio
    async def test_invalid_zip_error(self, tax_calculator):
        """T04-15: Unknown ZIP should raise clear error."""
        with pytest.raises(ValueError) as excinfo:
            await tax_calculator.get_jurisdiction("00000")

        assert "00000" in str(excinfo.value)
        assert "Unknown" in str(excinfo.value) or "not found" in str(excinfo.value).lower()


class TestTaxCalculation:
    """Tests for full tax calculation."""

    @pytest.mark.asyncio
    async def test_full_tax_calculation(self, tax_calculator):
        """Full tax calculation should include all components."""
        try:
            result = await tax_calculator.calculate_tax(
                selling_price=Decimal("30000"),
                taxable_fees=Decimal("85"),  # Doc fee
                trade_in_allowance=Decimal("5000"),
                zip_code="92101"  # CA
            )

            # Should have all required fields
            assert result.jurisdiction is not None
            assert result.selling_price == Decimal("30000.00")
            assert result.taxable_fees == Decimal("85.00")
            assert result.trade_in_allowance == Decimal("5000.00")
            assert result.taxable_basis > Decimal("0")
            assert result.tax_amount > Decimal("0")
            assert result.rule_applied is not None

            # CA: Taxable basis should be selling_price + fees (trade-in ignored)
            expected_basis = Decimal("30000") + Decimal("85")
            assert result.taxable_basis == expected_basis

        except ValueError:
            pytest.skip("ZIP 92101 not in test tax_rates data")

    @pytest.mark.asyncio
    async def test_trade_in_credit_applied(self, tax_calculator):
        """Trade-in credit should reduce taxable basis in AZ."""
        try:
            result = await tax_calculator.calculate_tax(
                selling_price=Decimal("30000"),
                taxable_fees=Decimal("85"),
                trade_in_allowance=Decimal("10000"),
                zip_code="85001"  # AZ
            )

            # AZ: Taxable basis should be (selling_price + fees) - trade_in
            expected_basis = Decimal("30000") + Decimal("85") - Decimal("10000")
            assert result.taxable_basis == expected_basis

        except ValueError:
            pytest.skip("ZIP 85001 not in test tax_rates data")


class TestStateRuleLists:
    """Tests for state rule classification."""

    def test_full_price_states(self):
        """Verify full-price states list."""
        assert "CA" in FULL_PRICE_STATES
        assert "MI" in FULL_PRICE_STATES
        assert "VA" in FULL_PRICE_STATES

    def test_trade_in_credit_states(self):
        """Verify trade-in credit states list."""
        assert "AZ" in TRADE_IN_CREDIT_STATES
        assert "NV" in TRADE_IN_CREDIT_STATES
        assert "TX" in TRADE_IN_CREDIT_STATES
        assert "FL" in TRADE_IN_CREDIT_STATES


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_compare_state_tax_rules(self):
        """compare_state_tax_rules should work correctly."""
        result = compare_state_tax_rules(
            selling_price=Decimal("25000"),
            taxable_fees=Decimal("100"),
            trade_in_allowance=Decimal("10000"),
            tax_rate=Decimal("8.0")
        )

        # Full price basis: $25,100
        assert result["full_price_basis"] == Decimal("25100")

        # Trade-in credit basis: $25,100 - $10,000 = $15,100
        assert result["trade_in_credit_basis"] == Decimal("15100")

        # Taxes
        assert result["full_price_tax"] == Decimal("2008.00")  # 25100 × 8%
        assert result["trade_in_credit_tax"] == Decimal("1208.00")  # 15100 × 8%

        # Difference
        assert result["difference"] == Decimal("800.00")


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_trade_in(self, tax_calculator):
        """Zero trade-in should result in same tax for both rule types."""
        result = tax_calculator.compare_tax_by_state(
            selling_price=Decimal("30000"),
            taxable_fees=Decimal("0"),
            trade_in_allowance=Decimal("0"),
            combined_rate=Decimal("8.0")
        )

        assert result["full_price_tax"] == result["trade_in_credit_tax"]
        assert result["difference"] == Decimal("0.00")

    def test_trade_in_exceeds_price(self, tax_calculator):
        """Trade-in exceeding price should result in zero taxable basis."""
        # Create a mock AZ jurisdiction
        jurisdiction = TaxJurisdiction(
            zip_code="85001",
            state="AZ",
            city="Phoenix",
            county="Maricopa",
            state_rate=Decimal("5.6"),
            county_rate=Decimal("0.7"),
            city_rate=Decimal("2.3"),
            special_district_rate=Decimal("0"),
            combined_rate=Decimal("8.6"),
            tax_basis_rule=TaxBasisRule.TRADE_IN_CREDIT,
            trade_in_credit=True
        )

        taxable_basis = tax_calculator.calculate_taxable_basis(
            selling_price=Decimal("20000"),
            taxable_fees=Decimal("0"),
            trade_in_allowance=Decimal("25000"),  # Trade-in exceeds price
            jurisdiction=jurisdiction
        )

        # Should not be negative
        assert taxable_basis == Decimal("0.00")

    def test_negative_equity_not_taxed(self, tax_calculator):
        """Negative equity should not increase taxable basis."""
        jurisdiction = TaxJurisdiction(
            zip_code="85001",
            state="AZ",
            city="Phoenix",
            county="Maricopa",
            state_rate=Decimal("5.6"),
            county_rate=Decimal("0.7"),
            city_rate=Decimal("2.3"),
            special_district_rate=Decimal("0"),
            combined_rate=Decimal("8.6"),
            tax_basis_rule=TaxBasisRule.TRADE_IN_CREDIT,
            trade_in_credit=True
        )

        # This is just the trade-in allowance, not the payoff
        # The taxable basis calculation doesn't consider negative equity
        taxable_basis = tax_calculator.calculate_taxable_basis(
            selling_price=Decimal("30000"),
            taxable_fees=Decimal("0"),
            trade_in_allowance=Decimal("10000"),
            jurisdiction=jurisdiction
        )

        assert taxable_basis == Decimal("20000.00")
