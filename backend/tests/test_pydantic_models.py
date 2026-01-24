"""
T01 Pydantic Model Validation Tests

Tests for CustomerProfile, DealJacket, ComplianceLog models.
Per tasks/T01_data_foundation.md
"""

import pytest
from datetime import datetime, date
from pydantic import ValidationError

# Import models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.customer import (
    CustomerProfile,
    CustomerIdentity,
    CustomerCreate,
    FCRAConsentEntry,
    PIIClearanceLevel,
    ResidenceType,
    ConsentType,
)
from app.models.deal import (
    DealJacket,
    DealCreate,
    DealStatus,
    DealType,
    TradeIn,
    TaxCalculation,
    AddOn,
    OfferingPriceComponents,
)
from app.models.compliance_log import (
    ComplianceLog,
    ComplianceLogCreate,
    EventType,
    Actor,
    AdverseActionReason,
    CreditDataUsed,
)


# ============================================================================
# T01-16: CustomerProfile Validation
# ============================================================================

def test_customer_profile_validation():
    """T01-16: CustomerProfile rejects invalid email format."""
    # Valid customer
    valid_customer = CustomerProfile(
        identity=CustomerIdentity(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
    )
    assert valid_customer.identity.email == "john.doe@example.com"

    # Invalid email should raise error
    with pytest.raises(ValidationError) as exc_info:
        CustomerProfile(
            identity=CustomerIdentity(
                first_name="John",
                last_name="Doe",
                email="invalid-email"
            )
        )
    assert "email" in str(exc_info.value).lower()


def test_customer_profile_uuid_validation():
    """CustomerProfile validates UUID v4 format."""
    # Valid UUID
    valid_customer = CustomerProfile(
        customer_id="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        identity=CustomerIdentity(first_name="Jane", last_name="Doe")
    )
    assert valid_customer.customer_id == "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"

    # Invalid UUID should raise error
    with pytest.raises(ValidationError):
        CustomerProfile(
            customer_id="not-a-valid-uuid",
            identity=CustomerIdentity(first_name="Jane", last_name="Doe")
        )


def test_customer_ssn_masked_format():
    """CustomerIdentity validates masked SSN format."""
    # Valid masked SSN
    identity = CustomerIdentity(
        first_name="John",
        last_name="Doe",
        ssn_masked="***-**-1234"
    )
    assert identity.ssn_masked == "***-**-1234"

    # Invalid format should raise error
    with pytest.raises(ValidationError):
        CustomerIdentity(
            first_name="John",
            last_name="Doe",
            ssn_masked="123-45-6789"  # Not masked
        )


def test_fcra_consent_entry():
    """FCRAConsentEntry validates fields correctly."""
    consent = FCRAConsentEntry(
        consent_id="consent_001",
        consent_type=ConsentType.SOFT_PULL,
        granted_at=datetime.utcnow(),
        ip_address="192.168.1.1",
        legal_text_version="v2026.1",
        expires_at=datetime.utcnow()
    )
    assert consent.consent_type == ConsentType.SOFT_PULL


# ============================================================================
# T01-17: DealJacket Validation
# ============================================================================

def test_deal_jacket_validation():
    """T01-17: DealJacket rejects negative selling_price."""
    # Valid deal
    valid_deal = DealJacket(
        deal_id="deal_001",
        customer_id="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        vehicle_id=1,
        selling_price=25000.00
    )
    assert valid_deal.selling_price == 25000.00

    # Negative price should raise error
    with pytest.raises(ValidationError) as exc_info:
        DealJacket(
            deal_id="deal_002",
            customer_id="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
            vehicle_id=1,
            selling_price=-5000.00
        )
    assert "selling_price" in str(exc_info.value).lower()


def test_deal_status_enum():
    """DealJacket validates deal_status enum."""
    deal = DealJacket(
        deal_id="deal_003",
        customer_id="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        vehicle_id=1,
        selling_price=25000.00,
        deal_status=DealStatus.WORKING
    )
    assert deal.deal_status == DealStatus.WORKING


def test_trade_in_negative_equity():
    """TradeIn calculates negative equity correctly."""
    trade = TradeIn(
        has_trade=True,
        allowance=15000.00,
        payoff_amount=18000.00  # Owes more than it's worth
    )

    # Should calculate negative equity
    assert trade.negative_equity_financed == 3000.00
    assert trade.equity_amount == 0


def test_tax_calculation_validation():
    """TaxCalculation validates all fields."""
    tax = TaxCalculation(
        jurisdiction_code="CA_SAN_DIEGO_92101",
        tax_rate_combined=0.0775,
        taxable_basis=25000.00,
        total_sales_tax=1937.50,
        rule_applied="CA_FULL_PRICE_BASIS"
    )
    assert tax.total_sales_tax == 1937.50


# ============================================================================
# T01-18: ComplianceLog Validation
# ============================================================================

def test_compliance_log_reason_codes():
    """T01-18: ComplianceLog validates reason code format."""
    # Valid reason code
    reason = AdverseActionReason(
        code="A01",
        text="Income insufficient for amount of credit requested"
    )
    assert reason.code == "A01"

    # Invalid code format should raise error
    with pytest.raises(ValidationError):
        AdverseActionReason(
            code="invalid",
            text="Some reason"
        )


def test_compliance_log_max_reasons():
    """ComplianceLog allows max 4 denial reasons per Reg B."""
    # 4 reasons should be OK
    log = ComplianceLog(
        event_type=EventType.ADVERSE_ACTION_GENERATED,
        credit_data_used=CreditDataUsed(
            bureau_source="Experian",
            score_date=date.today(),
            credit_score=620
        ),
        denial_reasons=[
            AdverseActionReason(code="A01", text="Reason 1"),
            AdverseActionReason(code="A02", text="Reason 2"),
            AdverseActionReason(code="A03", text="Reason 3"),
            AdverseActionReason(code="A04", text="Reason 4"),
        ]
    )
    assert len(log.denial_reasons) == 4

    # 5 reasons should fail
    with pytest.raises(ValidationError):
        ComplianceLog(
            event_type=EventType.ADVERSE_ACTION_GENERATED,
            credit_data_used=CreditDataUsed(
                bureau_source="Experian",
                score_date=date.today(),
                credit_score=620
            ),
            denial_reasons=[
                AdverseActionReason(code="A01", text="Reason 1"),
                AdverseActionReason(code="A02", text="Reason 2"),
                AdverseActionReason(code="A03", text="Reason 3"),
                AdverseActionReason(code="A04", text="Reason 4"),
                AdverseActionReason(code="A05", text="Reason 5"),
            ]
        )


def test_compliance_log_payload_hash():
    """ComplianceLog validates payload_hash format."""
    # Valid hash (64 hex chars)
    log = ComplianceLog(
        event_type=EventType.DISCLOSURE_PRESENTED,
        payload_hash="a" * 64
    )
    assert log.payload_hash == "a" * 64

    # Invalid hash should fail
    with pytest.raises(ValidationError):
        ComplianceLog(
            event_type=EventType.DISCLOSURE_PRESENTED,
            payload_hash="not-a-valid-hash"
        )


def test_adverse_action_requires_reasons():
    """Adverse action events must include denial reasons."""
    with pytest.raises(ValidationError):
        ComplianceLog(
            event_type=EventType.ADVERSE_ACTION_GENERATED,
            denial_reasons=[],  # Empty - should fail
            credit_data_used=CreditDataUsed(
                bureau_source="Experian",
                score_date=date.today(),
                credit_score=620
            )
        )


def test_adverse_action_requires_credit_data():
    """Adverse action events must include credit_data_used."""
    with pytest.raises(ValidationError):
        ComplianceLog(
            event_type=EventType.ADVERSE_ACTION_GENERATED,
            denial_reasons=[
                AdverseActionReason(code="A01", text="Reason 1")
            ],
            credit_data_used=None  # Should fail
        )


# ============================================================================
# T01-19: AddOn Benefit Statement Validation
# ============================================================================

def test_addon_benefit_statement():
    """T01-19: AddOn with benefit_statement=None and compliance_check_passed=True raises error."""
    # Valid: has benefit statement and passed
    valid_addon = AddOn(
        add_on_id="ao_001",
        name="Nitrogen Tire Fill",
        price=199.00,
        benefit_statement="Maintains tire pressure longer",
        compliance_check_passed=True
    )
    assert valid_addon.compliance_check_passed is True

    # Valid: no benefit statement and not passed
    valid_addon2 = AddOn(
        add_on_id="ao_002",
        name="Theft Etch",
        price=299.00,
        benefit_statement=None,
        compliance_check_passed=False
    )
    assert valid_addon2.compliance_check_passed is False

    # Invalid: no benefit but marked as passed
    with pytest.raises(ValidationError) as exc_info:
        AddOn(
            add_on_id="ao_003",
            name="Invalid Addon",
            price=100.00,
            benefit_statement=None,
            compliance_check_passed=True
        )
    assert "benefit_statement" in str(exc_info.value).lower()


def test_offering_price_components():
    """OfferingPriceComponents validates total matches sum."""
    # Valid: total matches
    valid = OfferingPriceComponents(
        base_vehicle_price=24000.00,
        doc_fee=85.00,
        mandatory_addons=[],
        total_offering_price=24085.00
    )
    assert valid.total_offering_price == 24085.00

    # Invalid: total doesn't match
    with pytest.raises(ValidationError):
        OfferingPriceComponents(
            base_vehicle_price=24000.00,
            doc_fee=85.00,
            mandatory_addons=[],
            total_offering_price=25000.00  # Wrong!
        )


# ============================================================================
# Additional Model Tests
# ============================================================================

def test_customer_create_model():
    """CustomerCreate validates input for new customers."""
    customer = CustomerCreate(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        state="CA",
        zip="92101"
    )
    assert customer.first_name == "John"


def test_deal_create_model():
    """DealCreate validates input for new deals."""
    deal = DealCreate(
        customer_id="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        vehicle_id=1,
        selling_price=25000.00,
        cash_down_payment=5000.00
    )
    assert deal.selling_price == 25000.00


def test_credit_data_used_validation():
    """CreditDataUsed validates FICO score range."""
    # Valid score
    credit = CreditDataUsed(
        bureau_source="Experian",
        score_date=date.today(),
        credit_score=720
    )
    assert credit.credit_score == 720

    # Invalid score (too low)
    with pytest.raises(ValidationError):
        CreditDataUsed(
            bureau_source="Experian",
            score_date=date.today(),
            credit_score=200  # Below 300
        )

    # Invalid score (too high)
    with pytest.raises(ValidationError):
        CreditDataUsed(
            bureau_source="Experian",
            score_date=date.today(),
            credit_score=900  # Above 850
        )
