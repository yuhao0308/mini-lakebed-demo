"""
T05: PII Scrubber Tests

Tests for PII redaction middleware.
Per tasks/T05_governance.md acceptance tests T05-10 through T05-17.
"""

import pytest
from app.middleware.pii_scrubber import PIIScrubber, get_pii_scrubber, ScrubbingResult
from app.models.authorization import ClearanceLevel


class TestPIIScrubber:
    """Tests for PIIScrubber middleware."""

    @pytest.fixture
    def scrubber(self) -> PIIScrubber:
        """Get PII scrubber instance."""
        return get_pii_scrubber()

    # T05-10: test_ssn_scrubbed
    def test_ssn_scrubbed(self, scrubber: PIIScrubber):
        """
        T05-10: SSN scrubbing.

        "123-45-6789" -> "***-**-6789"
        Per spec §5.3: SSN masked preserving last 4 digits.
        """
        result = scrubber.scrub_ssn("123-45-6789")
        assert result == "***-**-6789"

    def test_ssn_scrubbed_unformatted(self, scrubber: PIIScrubber):
        """Test SSN scrubbing for unformatted 9-digit SSN."""
        result = scrubber.scrub_ssn("123456789")
        assert result == "***-**-6789"

    def test_ssn_empty(self, scrubber: PIIScrubber):
        """Test SSN scrubbing with empty string."""
        result = scrubber.scrub_ssn("")
        assert result == ""

    def test_ssn_none(self, scrubber: PIIScrubber):
        """Test SSN scrubbing with None."""
        result = scrubber.scrub_ssn(None)
        assert result is None

    # T05-11: test_dob_scrubbed
    def test_dob_scrubbed(self, scrubber: PIIScrubber):
        """
        T05-11: DOB scrubbing.

        "1985-04-12" -> "1985-04-01"
        Per spec §5.3: Preserves year/month for age calculation.
        """
        result = scrubber.scrub_dob("1985-04-12")
        assert result == "1985-04-01"

    def test_dob_scrubbed_alternate_format(self, scrubber: PIIScrubber):
        """Test DOB scrubbing with MM/DD/YYYY format."""
        result = scrubber.scrub_dob("04/12/1985")
        assert result == "1985-04-01"

    def test_dob_empty(self, scrubber: PIIScrubber):
        """Test DOB scrubbing with empty string."""
        result = scrubber.scrub_dob("")
        assert result == ""

    # T05-12: test_email_scrubbed
    def test_email_scrubbed(self, scrubber: PIIScrubber):
        """
        T05-12: Email scrubbing.

        "john@example.com" -> "j****@example.com"
        Per spec §5.3: Preserves domain, masks local part.
        """
        result = scrubber.scrub_email("john@example.com")
        assert result == "j****@example.com"

    def test_email_scrubbed_long_local(self, scrubber: PIIScrubber):
        """Test email scrubbing with long local part."""
        result = scrubber.scrub_email("john.doe@example.com")
        assert result == "j****@example.com"

    def test_email_scrubbed_single_char(self, scrubber: PIIScrubber):
        """Test email scrubbing with single char local part."""
        result = scrubber.scrub_email("a@example.com")
        assert result == "****@example.com"

    def test_email_empty(self, scrubber: PIIScrubber):
        """Test email scrubbing with empty string."""
        result = scrubber.scrub_email("")
        assert result == ""

    def test_email_no_at_sign(self, scrubber: PIIScrubber):
        """Test email scrubbing with invalid email (no @)."""
        result = scrubber.scrub_email("notanemail")
        assert result == "notanemail"

    # T05-13: test_account_number_scrubbed
    def test_account_number_scrubbed(self, scrubber: PIIScrubber):
        """
        T05-13: Account number scrubbing.

        16-digit number masked preserving last 4.
        Per spec: Account numbers masked before LLM context.
        """
        result = scrubber.scrub_account_number("1234567890123456")
        assert result == "************3456"

    def test_account_number_10_digit(self, scrubber: PIIScrubber):
        """Test 10-digit account number scrubbing."""
        result = scrubber.scrub_account_number("1234567890")
        assert result == "******7890"

    def test_account_number_short(self, scrubber: PIIScrubber):
        """Test short account number scrubbing."""
        result = scrubber.scrub_account_number("123")
        assert result == "****"

    # T05-14: test_high_clearance_no_scrub
    def test_high_clearance_no_scrub(self, scrubber: PIIScrubber):
        """
        T05-14: High clearance returns original.

        Per spec §5.3: High clearance = full access (no scrubbing).
        """
        profile = {
            "ssn": "123-45-6789",
            "dob": "1985-04-12",
            "email": "john@example.com",
            "name": "John Doe"
        }

        result = scrubber.scrub_customer_profile(profile, ClearanceLevel.HIGH)

        assert result.scrubbing_applied is False
        assert result.scrubbed_data["ssn"] == "123-45-6789"
        assert result.scrubbed_data["dob"] == "1985-04-12"
        assert result.scrubbed_data["email"] == "john@example.com"
        assert len(result.fields_scrubbed) == 0

    # T05-15: test_low_clearance_full_scrub
    def test_low_clearance_full_scrub(self, scrubber: PIIScrubber):
        """
        T05-15: Low clearance masks all PII.

        Per spec §5.3: Low clearance = all PII masked.
        """
        profile = {
            "ssn": "123-45-6789",
            "dob": "1985-04-12",
            "email": "john@example.com",
            "phone": "555-123-4567",
            "name": "John Doe"
        }

        result = scrubber.scrub_customer_profile(profile, ClearanceLevel.LOW)

        assert result.scrubbing_applied is True
        assert result.scrubbed_data["ssn"] == "***-**-6789"
        assert result.scrubbed_data["dob"] == "1985-04-01"
        assert result.scrubbed_data["email"] == "j****@example.com"
        assert result.scrubbed_data["phone"] == "***-***-4567"
        # Name should not be scrubbed
        assert result.scrubbed_data["name"] == "John Doe"
        assert len(result.fields_scrubbed) >= 4

    # T05-16: test_llm_context_scrubbed
    def test_llm_context_scrubbed(self, scrubber: PIIScrubber):
        """
        T05-16: Data passed to LLM has no raw SSN.

        Per spec §5.3: LLM context must never contain raw SSN.
        """
        data = {
            "customer": {
                "ssn": "123-45-6789",
                "name": "John Doe"
            },
            "vehicle": {
                "vin": "1HGBH41JXMN109186",
                "price": 25000
            }
        }

        result = scrubber.scrub_for_llm_context(data)

        # SSN must be scrubbed
        assert result.scrubbed_data["customer"]["ssn"] == "***-**-6789"
        # Non-PII should be preserved
        assert result.scrubbed_data["customer"]["name"] == "John Doe"
        assert result.scrubbed_data["vehicle"]["vin"] == "1HGBH41JXMN109186"
        assert result.scrubbed_data["vehicle"]["price"] == 25000

    def test_llm_context_no_raw_ssn_in_text(self, scrubber: PIIScrubber):
        """Test that SSN patterns in text fields are also scrubbed."""
        data = {
            "notes": "Customer SSN is 123-45-6789, verified"
        }

        result = scrubber.scrub_for_llm_context(data)

        # SSN pattern should be scrubbed even in free text
        assert "123-45-6789" not in result.scrubbed_data["notes"]
        assert "***-**-6789" in result.scrubbed_data["notes"]

    # T05-17: test_nested_pii_found
    def test_nested_pii_found(self, scrubber: PIIScrubber):
        """
        T05-17: Recursively finds PII in nested structures.

        Per spec: Scrubber must handle deeply nested data.
        """
        data = {
            "deal": {
                "id": "deal_001",
                "customer": {
                    "profile": {
                        "ssn": "123-45-6789",
                        "contact": {
                            "email": "john@example.com",
                            "phone": "555-123-4567"
                        }
                    }
                }
            }
        }

        result = scrubber.scrub_for_llm_context(data)

        # All nested PII should be scrubbed
        customer = result.scrubbed_data["deal"]["customer"]["profile"]
        assert customer["ssn"] == "***-**-6789"
        assert customer["contact"]["email"] == "j****@example.com"
        assert customer["contact"]["phone"] == "***-***-4567"

    def test_list_scrubbing(self, scrubber: PIIScrubber):
        """Test that lists of items are properly scrubbed."""
        data = {
            "customers": [
                {"ssn": "111-22-3333", "name": "Alice"},
                {"ssn": "444-55-6666", "name": "Bob"}
            ]
        }

        result = scrubber.scrub_for_llm_context(data)

        assert result.scrubbed_data["customers"][0]["ssn"] == "***-**-3333"
        assert result.scrubbed_data["customers"][1]["ssn"] == "***-**-6666"
        # Names preserved
        assert result.scrubbed_data["customers"][0]["name"] == "Alice"
        assert result.scrubbed_data["customers"][1]["name"] == "Bob"


class TestScrubbingResult:
    """Tests for ScrubbingResult dataclass."""

    def test_scrubbing_result_structure(self):
        """Test ScrubbingResult has required fields."""
        result = ScrubbingResult(
            original_hash="abc123",
            scrubbed_data={"key": "value"},
            fields_scrubbed=["ssn"],
            scrubbing_applied=True
        )

        assert result.original_hash == "abc123"
        assert result.scrubbed_data == {"key": "value"}
        assert result.fields_scrubbed == ["ssn"]
        assert result.scrubbing_applied is True

    def test_scrubbing_result_audit_hash(self):
        """Test that ScrubbingResult includes hash for audit trail."""
        scrubber = get_pii_scrubber()
        data = {"ssn": "123-45-6789"}

        result = scrubber.scrub_for_llm_context(data)

        # Should have original hash for audit
        assert result.original_hash is not None
        assert len(result.original_hash) == 64  # SHA-256 hex


class TestMediumClearance:
    """Tests for medium clearance level behavior."""

    @pytest.fixture
    def scrubber(self) -> PIIScrubber:
        """Get PII scrubber instance."""
        return get_pii_scrubber()

    def test_medium_clearance_ssn_scrubbed(self, scrubber: PIIScrubber):
        """Medium clearance should still mask SSN."""
        profile = {"ssn": "123-45-6789"}

        result = scrubber.scrub_customer_profile(profile, ClearanceLevel.MEDIUM)

        assert result.scrubbed_data["ssn"] == "***-**-6789"

    def test_medium_clearance_dob_scrubbed(self, scrubber: PIIScrubber):
        """Medium clearance should mask DOB."""
        profile = {"dob": "1985-04-12"}

        result = scrubber.scrub_customer_profile(profile, ClearanceLevel.MEDIUM)

        assert result.scrubbed_data["dob"] == "1985-04-01"


class TestPhoneScrubbing:
    """Tests for phone number scrubbing."""

    @pytest.fixture
    def scrubber(self) -> PIIScrubber:
        """Get PII scrubber instance."""
        return get_pii_scrubber()

    def test_phone_formatted(self, scrubber: PIIScrubber):
        """Test formatted phone number scrubbing."""
        result = scrubber.scrub_phone("555-123-4567")
        assert result == "***-***-4567"

    def test_phone_unformatted(self, scrubber: PIIScrubber):
        """Test unformatted phone number scrubbing."""
        result = scrubber.scrub_phone("5551234567")
        assert result == "***-***-4567"

    def test_phone_empty(self, scrubber: PIIScrubber):
        """Test empty phone scrubbing."""
        result = scrubber.scrub_phone("")
        assert result == ""


class TestAddressScrubbing:
    """Tests for address scrubbing."""

    @pytest.fixture
    def scrubber(self) -> PIIScrubber:
        """Get PII scrubber instance."""
        return get_pii_scrubber()

    def test_address_street_number_masked(self, scrubber: PIIScrubber):
        """Test that street number is masked."""
        result = scrubber.scrub_address("123 Main St, Springfield, IL")
        assert result == "*** Main St, Springfield, IL"

    def test_address_preserves_city_state(self, scrubber: PIIScrubber):
        """Test that city/state is preserved."""
        result = scrubber.scrub_address("456 Oak Ave, Los Angeles, CA")
        assert "Los Angeles" in result
        assert "CA" in result
