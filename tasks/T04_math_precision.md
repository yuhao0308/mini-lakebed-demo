# T04: Math Precision (Penny-Perfect Calculations)

**Priority:** Medium
**Status:** Not Started
**Depends On:** T01 (Data Foundation)
**Blocked By:** T01

---

## Objective

Implement deterministic, penny-perfect financial calculations including all three day-count conventions (30/360, Actual/365, 365/360), state-specific tax rules, and arbitrary-precision arithmetic. This ensures quoted payments match final contracts exactly.

---

## Spec References

| Spec File | Section | Requirement |
|-----------|---------|-------------|
| `02_strategic_blueprint.md` | §1.1 The Crisis of Trust | "$0.01 variance can render a contract unfundable" |
| `02_strategic_blueprint.md` | §1.2 Neuro-Symbolic Reasoning | SMT solver for mathematically proven results |
| `02_strategic_blueprint.md` | §3.1 Agent 3: Fin_Calc_Solver | Penny-perfect deal structuring with deterministic formulas |
| `02_strategic_blueprint.md` | §4 User Story 3: Penny-Perfect Tax | Exact tax for specific zip code, not estimate |
| `02_strategic_blueprint.md` | §4 User Story 7: Penny-Perfect Payment | Monthly payment matches final contract exactly |
| `02_strategic_blueprint.md` | §6.2 Penny-Perfect Verification | 10,000 scenarios, 100% match within $0.01 |
| `03_implementation_dummy_data_plan.md` | §4. Deterministic Math Specifications | Arbitrary-precision arithmetic (Decimal) |
| `03_implementation_dummy_data_plan.md` | §4.1 Method A: 30/360 | Standard consumer loans |
| `03_implementation_dummy_data_plan.md` | §4.1 Method B: Actual/365 | Simple interest with daily accrual |
| `03_implementation_dummy_data_plan.md` | §4.1 Method C: 365/360 | Bank method (higher effective rate) |
| `03_implementation_dummy_data_plan.md` | §4.2 Tax Calculation Logic | CA taxes full price; AZ allows trade-in credit |
| `03_implementation_dummy_data_plan.md` | §6.1 Financial Completeness Checklist | $35k/5%/60mo = $660.49 exactly |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/services/day_count.py` | All three interest calculation methods |
| `backend/app/services/tax_calculator.py` | State-specific tax basis rules |
| `backend/app/services/deal_structurer.py` | Full deal structure calculation (replaces simple calculator) |
| `backend/app/models/financial.py` | Pydantic models with Decimal fields |
| `backend/tests/test_day_count_methods.py` | Unit tests for each interest method |
| `backend/tests/test_tax_calculation.py` | Tests for state-specific tax rules |
| `backend/tests/test_penny_perfect.py` | Regression suite for payment accuracy |

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/calculator.py` | Migrate to Decimal, integrate day_count methods |
| `backend/app/models/schemas.py` | Use `Decimal` for all currency/rate fields |
| `backend/app/routers/payments.py` | Use DealStructurer instead of simple calculator |

---

## Implementation Specifications

### day_count.py

```python
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass


class DayCountMethod(str, Enum):
    """
    Interest calculation day-count conventions.

    Ref: 03_implementation_dummy_data_plan.md §4.1
    """
    THIRTY_360 = "30/360"      # Standard consumer
    ACTUAL_365 = "actual/365"  # Simple interest
    BANK_365_360 = "365/360"   # Bank method


@dataclass
class InterestCalculation:
    """Result of interest calculation with audit trail."""
    principal: Decimal
    annual_rate: Decimal
    method: DayCountMethod
    period_interest: Decimal
    daily_rate: Decimal
    days_in_period: int


def calculate_monthly_rate(
    annual_rate: Decimal,
    method: DayCountMethod
) -> Decimal:
    """
    Calculate the monthly interest rate based on day-count method.

    30/360: rate / 12
    Actual/365: rate / 365 * days_in_month
    365/360: rate / 360 * days_in_month (effectively higher)
    """


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

    Actual/365 Method:
        I = P × R × (d/365)
        where d = actual days in period

    365/360 Method (Bank):
        I = P × R × (d/360)
        Effectively increases rate by 365/360 ≈ 1.39%
    """


def calculate_monthly_payment(
    principal: Decimal,
    annual_rate: Decimal,
    term_months: int,
    method: DayCountMethod = DayCountMethod.THIRTY_360
) -> Decimal:
    """
    Calculate monthly payment using amortization formula.

    Formula: P × [r(1+r)^n] / [(1+r)^n – 1]

    Uses Decimal for arbitrary precision.
    Rounds to 2 decimal places using ROUND_HALF_UP (banker's rounding).
    """


def verify_penny_perfect(
    calculated: Decimal,
    expected: Decimal,
    tolerance: Decimal = Decimal("0.01")
) -> bool:
    """
    Verify calculation matches expected within penny tolerance.

    Per spec: Any variance > $0.01 is a build failure.
    """
```

### tax_calculator.py

```python
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional


class TaxBasisRule(str, Enum):
    """
    State-specific tax basis calculation rules.

    Ref: 03_implementation_dummy_data_plan.md §4.2
    """
    FULL_PRICE = "FULL_PRICE"           # CA, MI, VA - Trade-in does NOT reduce tax
    TRADE_IN_CREDIT = "TRADE_IN_CREDIT"  # AZ, NV, TX - Trade-in reduces taxable basis


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
    AZ/NV/TX allow trade-in value to reduce taxable basis.

    Example from spec:
    - $50k car, $40k trade-in
    - CA (8%): Tax = $50,000 × 0.08 = $4,000
    - AZ (8%): Tax = ($50,000 - $40,000) × 0.08 = $800
    - Difference: $3,200
    """

    async def get_jurisdiction(
        self,
        zip_code: str
    ) -> TaxJurisdiction:
        """Load tax jurisdiction from reference data."""

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
        If state in [AZ, NV, TX]:
            basis = (selling_price + taxable_fees) - trade_in_allowance
        """

    def calculate_tax(
        self,
        selling_price: Decimal,
        taxable_fees: Decimal,
        trade_in_allowance: Decimal,
        zip_code: str
    ) -> TaxCalculation:
        """
        Full tax calculation with jurisdiction lookup and rule application.
        """
```

### deal_structurer.py

```python
from decimal import Decimal
from dataclasses import dataclass


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

    async def structure_deal(
        self,
        vehicle_id: int,
        customer_zip: str,
        fico_score: int,
        down_payment: Decimal,
        trade_in: Optional[TradeInDetails],
        requested_term: int
    ) -> DealStructure:
        """
        Build complete deal structure.

        Steps (per spec §2.3):
        1. Tax Determination - state-specific rules
        2. Fee Injection - mandatory state fees
        3. Lender Matching - best rate for tier/LTV
        4. Amortization - using lender's day-count method
        """

    def validate_payment_packing(
        self,
        deal: DealStructure
    ) -> bool:
        """
        Verify no hidden fees: monthly × term == total_of_payments

        Per spec §6.1: Any deviation suggests hidden fees.
        """

    def validate_ltv(
        self,
        deal: DealStructure,
        max_ltv: Decimal
    ) -> bool:
        """Verify LTV within lender constraints."""
```

### Financial Models (financial.py)

```python
from decimal import Decimal
from pydantic import BaseModel, Field


class MoneyField(Decimal):
    """Decimal with 2 decimal places for currency."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return Decimal(str(v)).quantize(Decimal("0.01"))


class RateField(Decimal):
    """Decimal with 4 decimal places for interest rates."""

    @classmethod
    def validate(cls, v):
        return Decimal(str(v)).quantize(Decimal("0.0001"))


class TradeInDetails(BaseModel):
    has_trade: bool
    allowance: MoneyField
    payoff_amount: MoneyField
    equity_amount: MoneyField  # Calculated: allowance - payoff
    negative_equity_financed: MoneyField  # If payoff > allowance
    vin: Optional[str] = None


class LendingTerms(BaseModel):
    lender_id: str
    program_tier: str
    term_months: int
    buy_rate: RateField
    contract_apr: RateField
    dealer_reserve: RateField
    days_basis: DayCountMethod
    amount_financed: MoneyField
    monthly_payment: MoneyField
    total_of_payments: MoneyField
    finance_charge: MoneyField
```

---

## Acceptance Tests

### Test File: `backend/tests/test_day_count_methods.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T04-01 | `test_30_360_monthly_rate` | 6% APR → 0.5% monthly |
| T04-02 | `test_actual_365_daily_rate` | 6% APR → 0.01644% daily |
| T04-03 | `test_365_360_effective_increase` | 365/360 increases effective rate by ~1.39% |
| T04-04 | `test_30_360_payment_35k_5pct_60mo` | $35,000 at 5% for 60mo = $660.49 |
| T04-05 | `test_actual_365_late_payment_interest` | 5 days late = 5 extra days interest |
| T04-06 | `test_365_360_disclosure_warning` | Consumer loan with 365/360 logs warning |
| T04-07 | `test_zero_rate_payment` | 0% APR calculates correctly (no division error) |
| T04-08 | `test_decimal_precision_no_drift` | 10,000 iterations maintain precision |

### Test File: `backend/tests/test_tax_calculation.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T04-09 | `test_ca_full_price_basis` | CA: $50k car, $40k trade → Tax on $50k |
| T04-10 | `test_az_trade_in_credit` | AZ: $50k car, $40k trade → Tax on $10k |
| T04-11 | `test_ca_az_difference_3200` | Same scenario: CA tax - AZ tax = $3,200 (at 8%) |
| T04-12 | `test_jurisdiction_lookup_92101` | Zip 92101 → San Diego, CA, 7.75% combined |
| T04-13 | `test_jurisdiction_lookup_85001` | Zip 85001 → Phoenix, AZ, 8.6% combined |
| T04-14 | `test_special_district_included` | Combined rate includes special district |
| T04-15 | `test_invalid_zip_error` | Unknown zip raises clear error |

### Test File: `backend/tests/test_penny_perfect.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T04-16 | `test_spec_example_35k_5pct_60mo` | Exactly $660.49 monthly (spec §6.1) |
| T04-17 | `test_negative_equity_added_to_loan` | Negative equity increases amount financed |
| T04-18 | `test_payment_packing_check_passes` | monthly × term == total_of_payments |
| T04-19 | `test_payment_packing_check_fails` | Hidden fee detected if sums don't match |
| T04-20 | `test_ltv_calculation_accurate` | LTV = amount_financed / vehicle_price |
| T04-21 | `test_finance_charge_accurate` | finance_charge = total_of_payments - amount_financed |
| T04-22 | `test_10000_scenarios_all_match` | Regression suite: all within $0.01 |

---

## Regression Test Suite

Per `02_strategic_blueprint.md` §6.2:

> We run a regression test suite of 10,000 deal scenarios... 100% of calculations must match within $0.01. Any variance triggers a build failure.

Create `backend/tests/fixtures/payment_scenarios.json`:

```json
[
  {
    "id": "scenario_001",
    "principal": 35000.00,
    "apr": 5.00,
    "term": 60,
    "method": "30/360",
    "expected_payment": 660.49
  },
  {
    "id": "scenario_002",
    "principal": 25000.00,
    "apr": 6.99,
    "term": 72,
    "method": "30/360",
    "expected_payment": 436.22
  }
  // ... 9,998 more scenarios
]
```

---

## Calculator Migration

Update `calculator.py` to use new infrastructure:

```python
# OLD
payment = principal * (
    (monthly_rate * (1 + monthly_rate) ** term_months) /
    ((1 + monthly_rate) ** term_months - 1)
)
return round(payment, 2)

# NEW
from decimal import Decimal
from app.services.day_count import calculate_monthly_payment, DayCountMethod

payment = calculate_monthly_payment(
    principal=Decimal(str(principal)),
    annual_rate=Decimal(str(apr)),
    term_months=term_months,
    method=DayCountMethod.THIRTY_360
)
# Returns Decimal already rounded to 2 places
```

---

## Definition of Done

- [ ] `day_count.py` implements all 3 methods with Decimal precision
- [ ] `tax_calculator.py` handles CA vs AZ rules correctly
- [ ] `deal_structurer.py` orchestrates full deal calculation
- [ ] All models use Decimal for money/rates
- [ ] `calculator.py` migrated to use new services
- [ ] 10,000-scenario regression fixture created
- [ ] All 22 acceptance tests pass
- [ ] CA/AZ tax difference demo works ($3,200 example)
- [ ] No floating-point drift in precision tests
- [ ] No regressions in existing tests
