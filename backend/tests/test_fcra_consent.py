"""
T03: FCRA Consent Tests

Tests for FCRA consent recording and validation.
Per tasks/T03_credit_flow.md
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta

from app.models.credit import ConsentType
from app.services.consent_manager import (
    ConsentManager,
    record_consent,
    check_consent,
    get_active_consent,
    get_consent_text,
    CONSENT_EXPIRATION_DAYS,
    _consents,
    _lock,
)


@pytest.fixture
def consent_manager():
    """Create a ConsentManager instance for testing."""
    return ConsentManager()


@pytest_asyncio.fixture
async def clean_customer():
    """Provide a clean customer ID and clean up after."""
    customer_id = f"test_customer_{datetime.utcnow().timestamp()}"
    manager = ConsentManager()
    await manager.clear_all_consents(customer_id)
    yield customer_id
    await manager.clear_all_consents(customer_id)


class TestConsentRecording:
    """Tests for consent recording functionality."""

    @pytest.mark.asyncio
    async def test_consent_recorded_with_ip(self, consent_manager, clean_customer):
        """T03-09: Consent record should include IP address."""
        test_ip = "192.168.1.100"

        record = await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address=test_ip,
            user_agent="Mozilla/5.0",
            legal_text_version="v2026.1"
        )

        assert record.ip_address == test_ip

    @pytest.mark.asyncio
    async def test_consent_recorded_with_timestamp(self, consent_manager, clean_customer):
        """T03-10: Consent record should include precise timestamp."""
        before = datetime.utcnow()

        record = await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version="v2026.1"
        )

        after = datetime.utcnow()

        assert record.granted_at is not None
        assert before <= record.granted_at <= after

    @pytest.mark.asyncio
    async def test_consent_expires_30_days(self, consent_manager, clean_customer):
        """T03-11: Consent expires_at should be 30 days from granted_at."""
        record = await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version="v2026.1"
        )

        expected_expiry = record.granted_at + timedelta(days=CONSENT_EXPIRATION_DAYS)

        # Allow 1 second tolerance for timing
        assert abs((record.expires_at - expected_expiry).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_expired_consent_invalid(self, consent_manager, clean_customer):
        """T03-12: Consent granted 31 days ago should return valid=False."""
        # Record consent
        record = await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version="v2026.1"
        )

        # Manually expire the consent by modifying expires_at
        async with _lock:
            if clean_customer in _consents:
                expired_record = _consents[clean_customer][ConsentType.SOFT_PULL.value]
                # Create a modified record with expired date
                from app.models.credit import ConsentRecord
                expired = ConsentRecord(
                    consent_id=expired_record.consent_id,
                    customer_id=expired_record.customer_id,
                    consent_type=expired_record.consent_type,
                    granted_at=expired_record.granted_at - timedelta(days=31),
                    ip_address=expired_record.ip_address,
                    user_agent=expired_record.user_agent,
                    legal_text_version=expired_record.legal_text_version,
                    expires_at=datetime.utcnow() - timedelta(days=1)  # Already expired
                )
                _consents[clean_customer][ConsentType.SOFT_PULL.value] = expired

        # Check consent validity
        result = await consent_manager.check_consent_valid(
            clean_customer, ConsentType.SOFT_PULL
        )

        assert result.valid is False
        assert result.requires_consent is True

    @pytest.mark.asyncio
    async def test_consent_legal_text_version(self, consent_manager, clean_customer):
        """T03-13: Consent record should include legal_text_version."""
        test_version = "v2026.1"

        record = await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version=test_version
        )

        assert record.legal_text_version == test_version

    @pytest.mark.asyncio
    async def test_consent_audit_logged(self, consent_manager, clean_customer):
        """T03-14: Consent should create audit log with event_type=soft_pull_consent."""
        from app.services.database import execute_query

        # Record consent
        record = await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version="v2026.1"
        )

        # Check audit log (use 'timestamp' column, not 'created_at')
        logs = await execute_query(
            """
            SELECT * FROM audit_logs
            WHERE session_id = ? AND event_type = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (clean_customer, "soft_pull_consent")
        )

        assert len(logs) > 0
        log = logs[0]
        assert log["event_type"] == "soft_pull_consent"
        assert log["session_id"] == clean_customer


class TestConsentValidation:
    """Tests for consent validation."""

    @pytest.mark.asyncio
    async def test_valid_consent_returns_true(self, consent_manager, clean_customer):
        """Valid consent should return valid=True."""
        await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version="v2026.1"
        )

        result = await consent_manager.check_consent_valid(
            clean_customer, ConsentType.SOFT_PULL
        )

        assert result.valid is True
        assert result.requires_consent is False
        assert result.consent is not None

    @pytest.mark.asyncio
    async def test_no_consent_returns_requires_consent(self, consent_manager, clean_customer):
        """No consent should return requires_consent=True."""
        result = await consent_manager.check_consent_valid(
            clean_customer, ConsentType.SOFT_PULL
        )

        assert result.valid is False
        assert result.requires_consent is True
        assert result.consent is None

    @pytest.mark.asyncio
    async def test_consent_type_specific(self, consent_manager, clean_customer):
        """Consent should be type-specific (soft_pull vs hard_pull)."""
        # Record soft pull consent
        await consent_manager.record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest",
            legal_text_version="v2026.1"
        )

        # Check soft pull - should be valid
        soft_result = await consent_manager.check_consent_valid(
            clean_customer, ConsentType.SOFT_PULL
        )
        assert soft_result.valid is True

        # Check hard pull - should not be valid
        hard_result = await consent_manager.check_consent_valid(
            clean_customer, ConsentType.HARD_PULL
        )
        assert hard_result.valid is False


class TestConsentLegalText:
    """Tests for consent legal text."""

    def test_legal_text_contains_fcra(self, consent_manager):
        """Legal text should mention FCRA."""
        text = consent_manager.get_consent_legal_text()
        assert "FCRA" in text or "Fair Credit Reporting Act" in text

    def test_legal_text_contains_dealer_name(self, consent_manager):
        """Legal text should include dealer name."""
        dealer = "Test Dealer Name"
        text = consent_manager.get_consent_legal_text(dealer_name=dealer)
        assert dealer in text

    def test_legal_text_soft_pull_disclosure(self, consent_manager):
        """Legal text should mention soft inquiry."""
        text = consent_manager.get_consent_legal_text()
        assert "soft" in text.lower()

    def test_legal_text_version_support(self, consent_manager):
        """Legal text should support different versions."""
        v1 = consent_manager.get_consent_legal_text(version="v2026.1")
        v2 = consent_manager.get_consent_legal_text(version="v2025.1")
        # Both should return valid text
        assert len(v1) > 50
        assert len(v2) > 50


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_record_consent_function(self, clean_customer):
        """Module-level record_consent should work."""
        record = await record_consent(
            customer_id=clean_customer,
            consent_type=ConsentType.SOFT_PULL,
            ip_address="127.0.0.1",
            user_agent="pytest"
        )
        assert record.customer_id == clean_customer

    @pytest.mark.asyncio
    async def test_check_consent_function(self, clean_customer):
        """Module-level check_consent should work."""
        result = await check_consent(clean_customer)
        assert result.valid is False  # No consent recorded

    def test_get_consent_text_function(self):
        """Module-level get_consent_text should work."""
        text = get_consent_text()
        assert len(text) > 50
        assert "FCRA" in text or "Fair Credit" in text
