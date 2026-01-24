"""
T04: Day Count Methods Tests

Tests for the three interest calculation methods:
- 30/360: Standard consumer loans
- Actual/365: Simple interest with daily accrual
- 365/360: Bank method

Per tasks/T04_math_precision.md
"""

import pytest
from decimal import Decimal
import logging

from app.services.day_count import (
    DayCountMethod,
    calculate_monthly_rate,
    calculate_daily_rate,
    calculate_period_interest,
    calculate_monthly_payment,
    verify_penny_perfect,
    get_effective_rate_increase,
    calculate_late_payment_interest,
    to_decimal,
    round_money
)


class TestMonthlyRate:
    """Tests for monthly rate calculation."""

    def test_30_360_monthly_rate(self):
        """T04-01: 6% APR using 30/360 should give 0.5% monthly rate."""
        annual_rate = Decimal("6.0")
        monthly_rate = calculate_monthly_rate(annual_rate, DayCountMethod.THIRTY_360)

        # 6% / 12 = 0.5% = 0.005
        expected = Decimal("0.005")
        assert monthly_rate == expected, f"Expected {expected}, got {monthly_rate}"

    def test_5_percent_monthly_rate(self):
        """5% APR using 30/360 should give ~0.4167% monthly rate."""
        annual_rate = Decimal("5.0")
        monthly_rate = calculate_monthly_rate(annual_rate, DayCountMethod.THIRTY_360)

        # 5% / 12 = 0.41667%
        expected = Decimal("0.004167")
        assert abs(monthly_rate - expected) < Decimal("0.000001")


class TestDailyRate:
    """Tests for daily rate calculation."""

    def test_actual_365_daily_rate(self):
        """T04-02: 6% APR using actual/365 should give ~0.01644% daily rate."""
        annual_rate = Decimal("6.0")
        daily_rate = calculate_daily_rate(annual_rate, DayCountMethod.ACTUAL_365)

        # 6% / 365 = 0.0164384%
        expected = Decimal("0.000164")  # 0.0164384% as decimal
        assert abs(daily_rate - expected) < Decimal("0.000001"), f"Expected ~{expected}, got {daily_rate}"

    def test_365_360_daily_rate(self):
        """365/360 uses 360-day year for daily rate."""
        annual_rate = Decimal("6.0")
        daily_rate = calculate_daily_rate(annual_rate, DayCountMethod.BANK_365_360)

        # 6% / 360 = 0.016667%
        expected = Decimal("0.000167")
        assert abs(daily_rate - expected) < Decimal("0.000001")


class TestEffectiveRateIncrease:
    """Tests for effective rate increase with 365/360 method."""

    def test_365_360_effective_increase(self):
        """T04-03: 365/360 increases effective rate by ~1.39%."""
        increase = get_effective_rate_increase(DayCountMethod.BANK_365_360)

        # 365/360 = 1.01389...
        expected = Decimal("365") / Decimal("360")
        assert abs(increase - expected) < Decimal("0.00001")

        # Check percentage increase
        percentage_increase = (increase - Decimal("1")) * 100
        assert Decimal("1.38") < percentage_increase < Decimal("1.40")

    def test_30_360_no_increase(self):
        """30/360 has no effective rate increase."""
        increase = get_effective_rate_increase(DayCountMethod.THIRTY_360)
        assert increase == Decimal("1")

    def test_actual_365_no_increase(self):
        """Actual/365 has no effective rate increase."""
        increase = get_effective_rate_increase(DayCountMethod.ACTUAL_365)
        assert increase == Decimal("1")


class TestPaymentCalculation:
    """Tests for monthly payment calculation."""

    def test_30_360_payment_35k_5pct_60mo(self):
        """T04-04: $35,000 at 5% for 60 months = $660.49 exactly (spec §6.1)."""
        payment = calculate_monthly_payment(
            principal=Decimal("35000"),
            annual_rate=Decimal("5.0"),
            term_months=60,
            method=DayCountMethod.THIRTY_360
        )

        expected = Decimal("660.49")
        assert payment == expected, f"Expected ${expected}, got ${payment}"

    def test_actual_365_late_payment_interest(self):
        """T04-05: 5 days late should accrue 5 days of interest."""
        principal = Decimal("10000")
        annual_rate = Decimal("6.0")
        days_late = 5

        interest = calculate_late_payment_interest(
            principal=principal,
            annual_rate=annual_rate,
            method=DayCountMethod.ACTUAL_365,
            days_late=days_late
        )

        # Daily interest = 10000 * 0.06 / 365 = 1.6438...
        # 5 days = ~8.22
        expected_daily = principal * (annual_rate / Decimal("100")) / Decimal("365")
        expected = round_money(expected_daily * days_late)

        assert interest == expected, f"Expected ${expected}, got ${interest}"

    def test_365_360_disclosure_warning(self, caplog):
        """T04-06: Consumer loan with 365/360 should log warning."""
        with caplog.at_level(logging.WARNING):
            calculate_period_interest(
                principal=Decimal("10000"),
                annual_rate=Decimal("6.0"),
                method=DayCountMethod.BANK_365_360,
                days_in_period=30
            )

        # Check that warning was logged about increased effective rate
        assert any("365/360" in record.message for record in caplog.records)

    def test_zero_rate_payment(self):
        """T04-07: 0% APR should calculate correctly without division error."""
        payment = calculate_monthly_payment(
            principal=Decimal("12000"),
            annual_rate=Decimal("0"),
            term_months=60,
            method=DayCountMethod.THIRTY_360
        )

        # At 0% interest: 12000 / 60 = 200
        expected = Decimal("200.00")
        assert payment == expected, f"Expected ${expected}, got ${payment}"

    def test_decimal_precision_no_drift(self):
        """T04-08: 10,000 iterations should maintain precision."""
        principal = Decimal("35000")
        rate = Decimal("5.0")
        term = 60

        # Calculate payment many times and verify consistency
        first_payment = calculate_monthly_payment(principal, rate, term)

        for i in range(10000):
            payment = calculate_monthly_payment(principal, rate, term)
            assert payment == first_payment, f"Iteration {i}: drift detected {payment} != {first_payment}"

        # Final verification against expected
        assert first_payment == Decimal("660.49")


class TestVerifyPennyPerfect:
    """Tests for penny-perfect verification."""

    def test_exact_match(self):
        """Exact match should return True."""
        assert verify_penny_perfect(Decimal("660.49"), Decimal("660.49"))

    def test_within_penny(self):
        """Within $0.01 should return True."""
        assert verify_penny_perfect(Decimal("660.49"), Decimal("660.50"))
        assert verify_penny_perfect(Decimal("660.50"), Decimal("660.49"))

    def test_beyond_penny(self):
        """Beyond $0.01 should return False."""
        assert not verify_penny_perfect(Decimal("660.49"), Decimal("660.52"))
        assert not verify_penny_perfect(Decimal("660.52"), Decimal("660.49"))


class TestPeriodInterest:
    """Tests for period interest calculation."""

    def test_30_360_period_interest(self):
        """30/360 method uses 30-day month regardless of actual days."""
        result = calculate_period_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("6.0"),
            method=DayCountMethod.THIRTY_360,
            days_in_period=31  # Actual days ignored for 30/360
        )

        # I = P * R / 12 = 10000 * 0.06 / 12 = 50.00
        assert result.period_interest == Decimal("50.00")
        assert result.method == DayCountMethod.THIRTY_360

    def test_actual_365_period_interest(self):
        """Actual/365 method uses actual days in period."""
        result = calculate_period_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("6.0"),
            method=DayCountMethod.ACTUAL_365,
            days_in_period=31
        )

        # I = P * R * (31/365) = 10000 * 0.06 * (31/365) = 50.96
        expected = round_money(Decimal("10000") * Decimal("0.06") * Decimal("31") / Decimal("365"))
        assert result.period_interest == expected

    def test_365_360_period_interest(self):
        """365/360 method uses actual days but 360-day year (higher interest)."""
        result = calculate_period_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("6.0"),
            method=DayCountMethod.BANK_365_360,
            days_in_period=31
        )

        # I = P * R * (31/360) = 10000 * 0.06 * (31/360) = 51.67
        expected = round_money(Decimal("10000") * Decimal("0.06") * Decimal("31") / Decimal("360"))
        assert result.period_interest == expected


class TestEdgeCases:
    """Tests for edge cases."""

    def test_large_principal(self):
        """Large principal should calculate correctly."""
        payment = calculate_monthly_payment(
            principal=Decimal("1000000"),  # $1 million
            annual_rate=Decimal("4.5"),
            term_months=360,  # 30-year loan
            method=DayCountMethod.THIRTY_360
        )

        # Should be around $5,066.85
        assert payment > Decimal("5000")
        assert payment < Decimal("5200")

    def test_high_rate(self):
        """High interest rate should calculate correctly."""
        payment = calculate_monthly_payment(
            principal=Decimal("10000"),
            annual_rate=Decimal("24.0"),  # 24% APR
            term_months=36,
            method=DayCountMethod.THIRTY_360
        )

        # Should be positive and reasonable
        assert payment > Decimal("0")
        assert payment < Decimal("500")

    def test_short_term(self):
        """Very short term should calculate correctly."""
        payment = calculate_monthly_payment(
            principal=Decimal("5000"),
            annual_rate=Decimal("6.0"),
            term_months=6,  # 6-month loan
            method=DayCountMethod.THIRTY_360
        )

        # Should be around $848
        assert payment > Decimal("840")
        assert payment < Decimal("860")
