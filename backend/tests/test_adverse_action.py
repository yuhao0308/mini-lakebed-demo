"""
T03: Adverse Action Tests

Tests for Regulation B compliant adverse action notice generation.
Per tasks/T03_credit_flow.md
"""

import pytest
import asyncio
from datetime import datetime, date

from app.models.credit import (
    CreditTier,
    CreditDecision,
    AdverseActionReason,
    CounterOffer,
)
from app.services.adverse_action import (
    AdverseActionService,
    map_factor_code,
    generate_notice,
    send_notice,
    FACTOR_CODE_MAPPING,
    FORBIDDEN_REASONS,
)


@pytest.fixture
def adverse_action_service():
    """Create an AdverseActionService instance for testing."""
    return AdverseActionService()


@pytest.fixture
def sample_decline_decision():
    """Create a sample declined credit decision."""
    return CreditDecision(
        decision="declined",
        tier=CreditTier.DECLINE,
        fico_score=540,
        decline_reasons=[
            AdverseActionReason(code="D02", text="Delinquent past or present credit obligations with others"),
            AdverseActionReason(code="D05", text="Ratio of balance to limit on bank revolving accounts is too high"),
        ],
        bureau_source="Experian",
        score_date=date.today()
    )


class TestFactorCodeMapping:
    """Tests for factor code to reason text mapping."""

    def test_factor_code_A01_mapping(self, adverse_action_service):
        """T03-15: Code 'A01' should map to income insufficient text."""
        reason = adverse_action_service.map_factor_code_to_reason("A01")
        assert reason.code == "A01"
        assert "income" in reason.text.lower()
        assert "insufficient" in reason.text.lower()

    def test_factor_code_A12_mapping(self, adverse_action_service):
        """T03-16: Code 'A12' should map to length of employment text."""
        reason = adverse_action_service.map_factor_code_to_reason("A12")
        assert reason.code == "A12"
        assert "employment" in reason.text.lower()

    def test_factor_code_04_mapping(self, adverse_action_service):
        """Bureau code '04' should map to high balance ratio text."""
        reason = adverse_action_service.map_factor_code_to_reason("04")
        assert reason.code == "04"
        assert "balance" in reason.text.lower() or "ratio" in reason.text.lower()

    def test_factor_code_12_mapping(self, adverse_action_service):
        """Bureau code '12' should map to delinquency text."""
        reason = adverse_action_service.map_factor_code_to_reason("12")
        assert reason.code == "12"
        assert "delinquen" in reason.text.lower() or "past due" in reason.text.lower()

    def test_unknown_factor_code_handled(self, adverse_action_service):
        """Unknown factor codes should still return valid reason."""
        reason = adverse_action_service.map_factor_code_to_reason("UNKNOWN_999")
        assert reason.code == "UNKNOWN_999"
        assert len(reason.text) > 0

    def test_all_mapped_codes_have_specific_text(self, adverse_action_service):
        """All mapped codes should have specific, non-generic text."""
        for code, text in FACTOR_CODE_MAPPING.items():
            reason = adverse_action_service.map_factor_code_to_reason(code)
            # Check not generic
            for forbidden in FORBIDDEN_REASONS:
                assert forbidden not in reason.text.lower(), \
                    f"Code {code} has forbidden text: {forbidden}"


class TestNoticeGeneration:
    """Tests for adverse action notice generation."""

    @pytest.mark.asyncio
    async def test_notice_max_4_reasons(self, adverse_action_service, sample_decline_decision):
        """T03-17: Notice should contain at most 4 principal reasons."""
        # Provide 6 factors - should only include 4
        bureau_factors = ["A01", "A02", "D02", "D05", "C03", "C04"]

        notice = await adverse_action_service.generate_notice(
            customer_id="test_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=bureau_factors
        )

        assert len(notice.principal_reasons) <= 4

    @pytest.mark.asyncio
    async def test_notice_no_generic_reasons(self, adverse_action_service, sample_decline_decision):
        """T03-18: Notice should not contain 'Bad Credit' or 'Internal Policy'."""
        notice = await adverse_action_service.generate_notice(
            customer_id="test_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=["D02", "D05"]
        )

        for reason in notice.principal_reasons:
            reason_lower = reason.text.lower()
            assert "bad credit" not in reason_lower
            assert "internal policy" not in reason_lower
            assert "credit score" not in reason_lower
            assert "proprietary" not in reason_lower

    @pytest.mark.asyncio
    async def test_notice_includes_bureau_source(self, adverse_action_service, sample_decline_decision):
        """T03-19: Notice should include bureau name."""
        notice = await adverse_action_service.generate_notice(
            customer_id="test_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=["D02"]
        )

        assert notice.bureau_source is not None
        assert notice.bureau_source in ["Equifax", "Experian", "TransUnion"]

    @pytest.mark.asyncio
    async def test_notice_includes_score_date(self, adverse_action_service, sample_decline_decision):
        """T03-20: Notice should include date credit was pulled."""
        notice = await adverse_action_service.generate_notice(
            customer_id="test_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=["D02"]
        )

        assert notice.score_date is not None
        assert isinstance(notice.score_date, date)

    @pytest.mark.asyncio
    async def test_notice_with_counter_offer(self, adverse_action_service):
        """T03-21: Conditional decline should include counter-offer terms."""
        counter_offer = CounterOffer(
            required_down_payment=5000.0,
            approved_apr=12.99,
            approved_term=48,
            monthly_payment=650.00,
            message="We can approve with a higher down payment."
        )

        decision = CreditDecision(
            decision="conditional",
            tier=CreditTier.NEAR_PRIME,
            fico_score=660,
            conditions=["Increase down payment to $5,000"],
            counter_offer=counter_offer,
            bureau_source="Experian",
            score_date=date.today()
        )

        notice = await adverse_action_service.generate_notice(
            customer_id="test_customer",
            credit_decision=decision,
            bureau_factors=["B01"]  # Collateral not sufficient
        )

        assert notice.counter_offer is not None
        assert notice.counter_offer.required_down_payment == 5000.0
        assert notice.counter_offer.approved_apr == 12.99
        assert notice.counter_offer.approved_term == 48

    @pytest.mark.asyncio
    async def test_notice_delivery_logged(self, adverse_action_service, sample_decline_decision):
        """T03-22: Notice delivery should create compliance log entry."""
        from app.services.database import execute_query

        notice = await adverse_action_service.generate_notice(
            customer_id="test_delivery_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=["D02"]
        )

        result = await adverse_action_service.send_notice(notice, "email")

        assert result.success is True
        assert result.delivery_method == "email"
        assert result.tracking_id is not None

        # Check audit log (use 'timestamp' column, not 'created_at')
        logs = await execute_query(
            """
            SELECT * FROM audit_logs
            WHERE session_id = ? AND event_type = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            ("test_delivery_customer", "adverse_action_delivered")
        )

        assert len(logs) > 0
        log = logs[0]
        assert log["event_type"] == "adverse_action_delivered"


class TestNoticeValidation:
    """Tests for notice compliance validation."""

    def test_validate_compliant_notice(self, adverse_action_service):
        """Valid notice should pass compliance validation."""
        from app.models.credit import AdverseActionNotice

        notice = AdverseActionNotice(
            notice_id="test_notice",
            customer_id="test_customer",
            generated_at=datetime.utcnow(),
            bureau_source="Experian",
            score_date=date.today(),
            fico_score=550,
            principal_reasons=[
                AdverseActionReason(code="D02", text="Delinquent credit obligations"),
                AdverseActionReason(code="D05", text="High balance ratio"),
            ]
        )

        valid, violations = adverse_action_service.validate_notice_compliance(notice)
        assert valid is True
        assert len(violations) == 0

    def test_validate_too_many_reasons(self, adverse_action_service):
        """Notice with >4 reasons should fail validation."""
        from app.models.credit import AdverseActionNotice

        # Create notice with 4 reasons first (model enforces max 4)
        notice = AdverseActionNotice(
            notice_id="test_notice",
            customer_id="test_customer",
            generated_at=datetime.utcnow(),
            bureau_source="Experian",
            score_date=date.today(),
            fico_score=550,
            principal_reasons=[
                AdverseActionReason(code=f"R{i}", text=f"Reason {i}")
                for i in range(4)  # 4 reasons (max allowed by model)
            ]
        )

        # Manually add a 5th reason to test validation logic
        # This bypasses Pydantic model validation to test the service validation
        notice.principal_reasons.append(
            AdverseActionReason(code="R5", text="Reason 5")
        )

        valid, violations = adverse_action_service.validate_notice_compliance(notice)
        assert valid is False
        assert any("more than 4" in v for v in violations)

    def test_validate_missing_bureau_source(self, adverse_action_service):
        """Notice with empty bureau source should fail validation."""
        from app.models.credit import AdverseActionNotice

        notice = AdverseActionNotice(
            notice_id="test_notice",
            customer_id="test_customer",
            generated_at=datetime.utcnow(),
            bureau_source="",  # Empty string (effectively missing)
            score_date=date.today(),
            fico_score=550,
            principal_reasons=[
                AdverseActionReason(code="D02", text="Delinquent credit obligations"),
            ]
        )

        valid, violations = adverse_action_service.validate_notice_compliance(notice)
        assert valid is False
        assert any("bureau" in v.lower() for v in violations)


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_map_factor_code_function(self):
        """Module-level map_factor_code should work."""
        reason = map_factor_code("A01")
        assert reason.code == "A01"
        assert "income" in reason.text.lower()

    @pytest.mark.asyncio
    async def test_generate_notice_function(self, sample_decline_decision):
        """Module-level generate_notice should work."""
        notice = await generate_notice(
            customer_id="test_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=["D02"]
        )
        assert notice.notice_id is not None
        assert notice.customer_id == "test_customer"

    @pytest.mark.asyncio
    async def test_send_notice_function(self, sample_decline_decision):
        """Module-level send_notice should work."""
        notice = await generate_notice(
            customer_id="test_customer",
            credit_decision=sample_decline_decision,
            bureau_factors=["D02"]
        )

        result = await send_notice(notice, "download")
        assert result.success is True
        assert result.delivery_method == "download"
