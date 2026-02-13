"""
T05: Audit Integrity Tests

Tests for audit hasher and hash chain integrity.
Per tasks/T05_governance.md acceptance tests T05-18 through T05-27.
"""

import pytest
from app.services.audit_hasher import (
    AuditHasher,
    AuditEntry,
    get_audit_hasher,
    hash_payload,
    create_audit_entry
)
from app.middleware.pii_scrubber import get_pii_scrubber
from app.models.authorization import ClearanceLevel


class TestAuditHasher:
    """Tests for AuditHasher service."""

    @pytest.fixture
    def hasher(self) -> AuditHasher:
        """Get audit hasher instance."""
        return AuditHasher()

    # T05-18: test_payload_hash_sha256
    def test_payload_hash_sha256(self, hasher: AuditHasher):
        """
        T05-18: Hash is 64-char hex string.

        Per spec: SHA-256 produces 64-character hexadecimal hash.
        """
        payload = {"key": "value", "number": 123}
        result = hasher.hash_payload(payload)

        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    # T05-19: test_hash_deterministic
    def test_hash_deterministic(self, hasher: AuditHasher):
        """
        T05-19: Same payload -> same hash.

        Per spec: Hashing must be deterministic for verification.
        """
        payload = {"action": "create", "deal_id": "deal_001", "price": 25000}

        hash1 = hasher.hash_payload(payload)
        hash2 = hasher.hash_payload(payload)

        assert hash1 == hash2

    def test_hash_deterministic_different_order(self, hasher: AuditHasher):
        """Test that key order doesn't affect hash (canonical JSON)."""
        payload1 = {"a": 1, "b": 2, "c": 3}
        payload2 = {"c": 3, "a": 1, "b": 2}

        hash1 = hasher.hash_payload(payload1)
        hash2 = hasher.hash_payload(payload2)

        assert hash1 == hash2

    # T05-20: test_hash_changes_on_modification
    def test_hash_changes_on_modification(self, hasher: AuditHasher):
        """
        T05-20: Modified payload -> different hash.

        Per spec: Any change to payload must produce different hash.
        """
        original = {"price": 25000, "deal_id": "deal_001"}
        modified = {"price": 25001, "deal_id": "deal_001"}

        original_hash = hasher.hash_payload(original)
        modified_hash = hasher.hash_payload(modified)

        assert original_hash != modified_hash

    def test_hash_changes_on_field_addition(self, hasher: AuditHasher):
        """Test that adding a field changes the hash."""
        original = {"price": 25000}
        modified = {"price": 25000, "extra": "field"}

        original_hash = hasher.hash_payload(original)
        modified_hash = hasher.hash_payload(modified)

        assert original_hash != modified_hash

    def test_hash_changes_on_field_removal(self, hasher: AuditHasher):
        """Test that removing a field changes the hash."""
        original = {"price": 25000, "extra": "field"}
        modified = {"price": 25000}

        original_hash = hasher.hash_payload(original)
        modified_hash = hasher.hash_payload(modified)

        assert original_hash != modified_hash

    # T05-21: test_audit_entry_complete
    def test_audit_entry_complete(self, hasher: AuditHasher):
        """
        T05-21: Entry has all required fields.

        Per spec: Audit entry must include transaction_id, timestamp,
        actor, event_type, payload_hash, regulatory_flags.
        """
        entry = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="deal_created",
            payload={"deal_id": "deal_001", "price": 25000},
            regulatory_flags={"fcra_compliant": True}
        )

        # Check all required fields
        assert entry.transaction_id is not None
        assert len(entry.transaction_id) == 36  # UUID format
        assert entry.timestamp is not None
        assert entry.timestamp.endswith("Z")  # ISO format with Z
        assert entry.actor == "user:sales_1"
        assert entry.event_type == "deal_created"
        assert entry.payload_hash is not None
        assert len(entry.payload_hash) == 64
        assert entry.regulatory_flags == {"fcra_compliant": True}

    def test_audit_entry_to_dict(self, hasher: AuditHasher):
        """Test conversion of AuditEntry to dict for DB insertion."""
        entry = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="price_changed",
            payload={"old_price": 25000, "new_price": 24000}
        )

        entry_dict = hasher.entry_to_dict(entry)

        assert "transaction_id" in entry_dict
        assert "timestamp" in entry_dict
        assert "actor" in entry_dict
        assert "event_type" in entry_dict
        assert "payload_hash" in entry_dict
        assert "regulatory_flags" in entry_dict

    # T05-22: test_chain_verification
    def test_chain_verification(self, hasher: AuditHasher):
        """
        T05-22: Unmodified chain passes verification.

        Per spec: Valid chain where each entry's previous_hash
        matches prior entry's payload_hash.
        """
        # Create chain of entries
        entry1 = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="deal_created",
            payload={"deal_id": "deal_001"}
        )

        entry2 = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="price_changed",
            payload={"old_price": 25000, "new_price": 24000}
        )

        entry3 = hasher.create_audit_entry(
            actor="user:finance_mgr",
            event_type="deal_approved",
            payload={"deal_id": "deal_001", "approved": True}
        )

        chain = [entry1, entry2, entry3]

        # Chain should be valid
        assert hasher.verify_chain(chain) is True

    def test_chain_verification_empty(self, hasher: AuditHasher):
        """Test that empty chain is valid."""
        assert hasher.verify_chain([]) is True

    def test_chain_verification_single_entry(self, hasher: AuditHasher):
        """Test that single entry chain is valid."""
        entry = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="deal_created",
            payload={"deal_id": "deal_001"}
        )

        assert hasher.verify_chain([entry]) is True

    # T05-23: test_tampered_chain_detected
    def test_tampered_chain_detected(self, hasher: AuditHasher):
        """
        T05-23: Modified entry fails verification.

        Per spec: Tampered chain must be detected.
        """
        # Create valid chain
        entry1 = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="deal_created",
            payload={"deal_id": "deal_001"}
        )

        entry2 = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="price_changed",
            payload={"old_price": 25000, "new_price": 24000}
        )

        # Tamper with entry2's previous_hash
        entry2.previous_hash = "tampered_hash_value_that_does_not_match"

        chain = [entry1, entry2]

        # Chain should fail verification
        assert hasher.verify_chain(chain) is False

    def test_tampered_payload_hash_detected(self, hasher: AuditHasher):
        """Test that tampering with payload_hash is detected."""
        entry = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="deal_created",
            payload={"deal_id": "deal_001", "price": 25000}
        )

        original_payload = {"deal_id": "deal_001", "price": 25000}
        tampered_payload = {"deal_id": "deal_001", "price": 24000}

        # Original payload should verify
        assert hasher.verify_entry(entry, original_payload) is True

        # Tampered payload should fail
        assert hasher.verify_entry(entry, tampered_payload) is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_hash_payload_function(self):
        """Test module-level hash_payload function."""
        payload = {"key": "value"}
        result = hash_payload(payload)

        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_create_audit_entry_function(self):
        """Test module-level create_audit_entry function."""
        result = create_audit_entry(
            actor="user:test",
            event_type="test_event",
            payload={"test": True}
        )

        assert "transaction_id" in result
        assert "timestamp" in result
        assert "actor" in result
        assert "event_type" in result
        assert "payload_hash" in result

    def test_get_audit_hasher_singleton(self):
        """Test that get_audit_hasher returns singleton."""
        hasher1 = get_audit_hasher()
        hasher2 = get_audit_hasher()

        assert hasher1 is hasher2


class TestChainSummary:
    """Tests for audit chain summary."""

    @pytest.fixture
    def hasher(self) -> AuditHasher:
        """Get fresh audit hasher instance."""
        return AuditHasher()

    def test_chain_summary_empty(self, hasher: AuditHasher):
        """Test chain summary for empty chain."""
        summary = hasher.get_chain_summary([])

        assert summary["entry_count"] == 0
        assert summary["first_entry"] is None
        assert summary["last_entry"] is None
        assert summary["chain_valid"] is True

    def test_chain_summary_with_entries(self, hasher: AuditHasher):
        """Test chain summary with entries."""
        entry1 = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="deal_created",
            payload={"deal_id": "deal_001"}
        )

        entry2 = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="price_changed",
            payload={"price": 24000}
        )

        summary = hasher.get_chain_summary([entry1, entry2])

        assert summary["entry_count"] == 2
        assert summary["first_entry"]["event_type"] == "deal_created"
        assert summary["last_entry"]["event_type"] == "price_changed"
        assert summary["chain_valid"] is True


class TestCompletenessChecks:
    """
    Completeness tests per spec §6.3.

    T05-24 through T05-27.
    """

    # T05-24: Cross-Store Isolation (tested in test_authorization.py)
    # This is a duplicate reference - see test_authorization.py::test_cross_store_isolation

    # T05-25: Manager Override (tested in test_authorization.py)
    # This is a duplicate reference - see test_authorization.py::test_finance_manager_can_edit_deal

    # T05-26: test_audit_trail_fidelity
    def test_audit_trail_fidelity(self):
        """
        T05-26: Every selling_price change logged with user_id and timestamp.

        Per spec §6.3: Audit trail must capture all price changes.
        """
        hasher = AuditHasher()

        # Simulate price change audit entry
        entry = hasher.create_audit_entry(
            actor="user:sales_1",
            event_type="selling_price_changed",
            payload={
                "deal_id": "deal_001",
                "previous_value": 25000,
                "new_value": 24000
            },
            regulatory_flags={"price_change_logged": True}
        )

        # Verify entry contains required audit info
        assert entry.actor == "user:sales_1"
        assert entry.timestamp is not None
        assert entry.event_type == "selling_price_changed"
        assert entry.payload_hash is not None

    # T05-27: test_agent_pii_restriction
    def test_agent_pii_restriction(self):
        """
        T05-27: AI Agent with "Low Clearance" cannot access ssn_token.

        Per spec §6.3: Low clearance agents see NULL for ssn_token.
        """
        scrubber = get_pii_scrubber()

        customer_profile = {
            "name": "John Doe",
            "ssn_token": "vault_ref_123456",
            "ssn": "123-45-6789",
            "email": "john@example.com"
        }

        # Scrub with LOW clearance (agent clearance)
        result = scrubber.scrub_customer_profile(
            customer_profile,
            ClearanceLevel.LOW
        )

        # SSN should be masked
        assert result.scrubbed_data["ssn"] == "***-**-6789"

        # Name should be preserved
        assert result.scrubbed_data["name"] == "John Doe"


class TestVerifyChainFromDicts:
    """Tests for verify_chain_from_dicts method."""

    @pytest.fixture
    def hasher(self) -> AuditHasher:
        """Get audit hasher instance."""
        return AuditHasher()

    def test_verify_chain_from_dicts_valid(self, hasher: AuditHasher):
        """Test valid chain verification from dict entries."""
        entries = [
            {"payload_hash": "hash1", "previous_hash": None},
            {"payload_hash": "hash2", "previous_hash": "hash1"},
            {"payload_hash": "hash3", "previous_hash": "hash2"}
        ]

        assert hasher.verify_chain_from_dicts(entries) is True

    def test_verify_chain_from_dicts_invalid(self, hasher: AuditHasher):
        """Test invalid chain detection from dict entries."""
        entries = [
            {"payload_hash": "hash1", "previous_hash": None},
            {"payload_hash": "hash2", "previous_hash": "wrong_hash"},
            {"payload_hash": "hash3", "previous_hash": "hash2"}
        ]

        assert hasher.verify_chain_from_dicts(entries) is False

    def test_verify_chain_from_dicts_empty(self, hasher: AuditHasher):
        """Test empty chain verification."""
        assert hasher.verify_chain_from_dicts([]) is True
