"""
T05: Audit Hasher Service

Cryptographic audit trail for tamper evidence.
Per tasks/T05_governance.md and 03_implementation_dummy_data_plan.md

Creates SHA-256 hashes of payloads for immutability verification.
Implements Merkle-style hash chain for audit log integrity.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Optional, List, Dict
from dataclasses import dataclass, field


@dataclass
class AuditEntry:
    """A complete audit log entry with hash."""
    transaction_id: str
    timestamp: str
    actor: str
    event_type: str
    payload_hash: str
    previous_hash: Optional[str] = None
    regulatory_flags: Dict[str, Any] = field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None  # Original payload (optional)


class AuditHasher:
    """
    Cryptographic audit trail for tamper evidence.

    Per spec: Creates SHA-256 hash of payloads for immutability verification.

    Features:
    - Deterministic hashing using canonical JSON
    - Hash chain for tamper detection
    - Support for regulatory flag tracking
    """

    def __init__(self):
        """Initialize the audit hasher."""
        self._last_hash: Optional[str] = None
        self._entry_count: int = 0

    def hash_payload(self, payload: Any) -> str:
        """
        Generate SHA-256 hash of payload.

        Serializes to canonical JSON (sorted keys, no whitespace)
        for consistent hashing.

        Args:
            payload: Any JSON-serializable data

        Returns:
            64-character hexadecimal hash string
        """
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(',', ':'),
            default=str  # Handle datetime, Decimal, etc.
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def create_audit_entry(
        self,
        actor: str,
        event_type: str,
        payload: Any,
        regulatory_flags: Optional[Dict[str, Any]] = None,
        include_payload: bool = False
    ) -> AuditEntry:
        """
        Create complete audit log entry with hash.

        Args:
            actor: User or system that performed the action
            event_type: Type of event (e.g., "deal_created", "price_changed")
            payload: Data associated with the event
            regulatory_flags: Regulatory compliance flags
            include_payload: Whether to include original payload in entry

        Returns:
            AuditEntry ready for database insertion
        """
        payload_hash = self.hash_payload(payload)
        timestamp = datetime.utcnow().isoformat() + "Z"
        transaction_id = str(uuid.uuid4())

        entry = AuditEntry(
            transaction_id=transaction_id,
            timestamp=timestamp,
            actor=actor,
            event_type=event_type,
            payload_hash=payload_hash,
            previous_hash=self._last_hash,
            regulatory_flags=regulatory_flags or {},
            payload=payload if include_payload else None
        )

        # Update chain
        self._last_hash = payload_hash
        self._entry_count += 1

        return entry

    def entry_to_dict(self, entry: AuditEntry) -> Dict[str, Any]:
        """
        Convert AuditEntry to dictionary for database insertion.

        Args:
            entry: AuditEntry to convert

        Returns:
            Dictionary with all required fields
        """
        result = {
            "transaction_id": entry.transaction_id,
            "timestamp": entry.timestamp,
            "actor": entry.actor,
            "event_type": entry.event_type,
            "payload_hash": entry.payload_hash,
            "previous_hash": entry.previous_hash,
            "regulatory_flags": json.dumps(entry.regulatory_flags)
        }

        if entry.payload is not None:
            result["payload"] = json.dumps(entry.payload)

        return result

    def verify_entry(self, entry: AuditEntry, original_payload: Any) -> bool:
        """
        Verify a single audit entry against original payload.

        Args:
            entry: AuditEntry to verify
            original_payload: Original data that was hashed

        Returns:
            True if hash matches, False if tampered
        """
        computed_hash = self.hash_payload(original_payload)
        return computed_hash == entry.payload_hash

    def verify_chain(self, entries: List[AuditEntry]) -> bool:
        """
        Verify audit log chain integrity.

        Each entry's previous_hash should match the prior entry's payload_hash.

        Args:
            entries: List of AuditEntry objects in chronological order

        Returns:
            True if chain is valid, False if tampered
        """
        if not entries:
            return True

        for i, entry in enumerate(entries):
            if i == 0:
                # First entry should have no previous hash or match a known root
                continue

            previous_entry = entries[i - 1]
            if entry.previous_hash != previous_entry.payload_hash:
                return False

        return True

    def verify_chain_from_dicts(self, entries: List[Dict[str, Any]]) -> bool:
        """
        Verify chain from dictionary entries (e.g., from database).

        Args:
            entries: List of entry dictionaries in chronological order

        Returns:
            True if chain is valid, False if tampered
        """
        if not entries:
            return True

        for i, entry in enumerate(entries):
            if i == 0:
                continue

            previous_entry = entries[i - 1]
            if entry.get("previous_hash") != previous_entry.get("payload_hash"):
                return False

        return True

    def get_chain_summary(self, entries: List[AuditEntry]) -> Dict[str, Any]:
        """
        Get summary of audit chain for reporting.

        Args:
            entries: List of AuditEntry objects

        Returns:
            Summary with chain info and integrity status
        """
        if not entries:
            return {
                "entry_count": 0,
                "first_entry": None,
                "last_entry": None,
                "chain_valid": True
            }

        return {
            "entry_count": len(entries),
            "first_entry": {
                "transaction_id": entries[0].transaction_id,
                "timestamp": entries[0].timestamp,
                "event_type": entries[0].event_type
            },
            "last_entry": {
                "transaction_id": entries[-1].transaction_id,
                "timestamp": entries[-1].timestamp,
                "event_type": entries[-1].event_type
            },
            "chain_valid": self.verify_chain(entries)
        }


# Module-level singleton
_hasher: Optional[AuditHasher] = None


def get_audit_hasher() -> AuditHasher:
    """Get or create the audit hasher singleton."""
    global _hasher
    if _hasher is None:
        _hasher = AuditHasher()
    return _hasher


def hash_payload(payload: Any) -> str:
    """Convenience function to hash a payload."""
    return get_audit_hasher().hash_payload(payload)


def create_audit_entry(
    actor: str,
    event_type: str,
    payload: Any,
    regulatory_flags: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to create an audit entry.

    Returns dictionary ready for database insertion.
    """
    hasher = get_audit_hasher()
    entry = hasher.create_audit_entry(actor, event_type, payload, regulatory_flags)
    return hasher.entry_to_dict(entry)
