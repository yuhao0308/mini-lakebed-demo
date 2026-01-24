"""
T03: FCRA Consent Manager

FCRA consent tracking with full audit trail.
Per tasks/T03_credit_flow.md
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio

from app.models.credit import (
    ConsentType,
    ConsentRecord,
    ConsentCheckResult,
)
from app.services.database import execute_insert, execute_query


# In-memory consent store (for demo purposes)
# Key: customer_id -> Dict[consent_type -> ConsentRecord]
_consents: Dict[str, Dict[str, ConsentRecord]] = {}
_lock = asyncio.Lock()

# Consent expiration period in days
CONSENT_EXPIRATION_DAYS = 30

# Legal text versions
LEGAL_TEXTS = {
    "v2026.1": (
        "I understand that by clicking 'Submit', I am providing 'written instructions' "
        "under the Fair Credit Reporting Act (FCRA) authorizing {dealer_name} to obtain "
        "personal credit information from one or more consumer reporting agencies solely "
        "for pre-qualification purposes. This is a soft inquiry and will not affect my "
        "credit score."
    ),
    "v2025.1": (
        "By clicking 'Submit', I authorize {dealer_name} to obtain a consumer credit report "
        "for pre-qualification purposes under the FCRA. This soft inquiry will not affect "
        "my credit score."
    ),
}


class ConsentManager:
    """
    FCRA consent tracking with full audit trail.
    """

    async def record_consent(
        self,
        customer_id: str,
        consent_type: ConsentType,
        ip_address: str,
        user_agent: str,
        legal_text_version: str = "v2026.1"
    ) -> ConsentRecord:
        """
        Record FCRA consent with all required metadata.

        Consent expires after 30 days per spec.
        """
        async with _lock:
            consent_id = f"consent_{uuid.uuid4().hex[:12]}"
            granted_at = datetime.utcnow()
            expires_at = granted_at + timedelta(days=CONSENT_EXPIRATION_DAYS)

            record = ConsentRecord(
                consent_id=consent_id,
                customer_id=customer_id,
                consent_type=consent_type,
                granted_at=granted_at,
                ip_address=ip_address,
                user_agent=user_agent,
                legal_text_version=legal_text_version,
                expires_at=expires_at
            )

            # Store in memory
            if customer_id not in _consents:
                _consents[customer_id] = {}
            _consents[customer_id][consent_type.value] = record

            # Log to audit trail
            await self._log_consent_event(record)

            return record

    async def get_active_consent(
        self,
        customer_id: str,
        consent_type: ConsentType
    ) -> Optional[ConsentRecord]:
        """
        Get active (non-expired) consent for customer.
        """
        async with _lock:
            if customer_id not in _consents:
                return None

            record = _consents[customer_id].get(consent_type.value)
            if not record:
                return None

            # Check if expired
            if datetime.utcnow() > record.expires_at:
                return None

            return record

    async def check_consent_valid(
        self,
        customer_id: str,
        consent_type: ConsentType = ConsentType.SOFT_PULL
    ) -> ConsentCheckResult:
        """
        Check if valid consent exists for customer.
        """
        consent = await self.get_active_consent(customer_id, consent_type)

        if consent:
            return ConsentCheckResult(
                valid=True,
                requires_consent=False,
                consent=consent,
                message="Valid consent found"
            )

        return ConsentCheckResult(
            valid=False,
            requires_consent=True,
            consent=None,
            message="FCRA consent required before credit check"
        )

    def get_consent_legal_text(
        self,
        version: str = "v2026.1",
        dealer_name: str = "Mini-Lakebed Demo Dealer"
    ) -> str:
        """
        Return the specific legal text for consent UI.
        """
        text = LEGAL_TEXTS.get(version, LEGAL_TEXTS["v2026.1"])
        return text.format(dealer_name=dealer_name)

    async def _log_consent_event(self, record: ConsentRecord) -> None:
        """Log consent event to audit_logs table."""
        transaction_id = str(uuid.uuid4())

        payload = {
            "consent_id": record.consent_id,
            "customer_id": record.customer_id,
            "consent_type": record.consent_type.value,
            "granted_at": record.granted_at.isoformat(),
            "ip_address": record.ip_address,
            "legal_text_version": record.legal_text_version,
            "expires_at": record.expires_at.isoformat()
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        regulatory_flags = {
            "fcra_consent_recorded": True,
            "consent_type": record.consent_type.value
        }

        try:
            await execute_insert(
                """
                INSERT INTO audit_logs (
                    session_id, action, transaction_id, actor, event_type,
                    payload_hash, regulatory_flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.customer_id,
                    f"consent:{record.consent_type.value}",
                    transaction_id,
                    "agent:credit_officer",
                    "soft_pull_consent",
                    payload_hash,
                    json.dumps(regulatory_flags)
                )
            )
        except Exception as e:
            print(f"Warning: Failed to log consent event: {e}")

    async def revoke_consent(
        self,
        customer_id: str,
        consent_type: ConsentType
    ) -> bool:
        """Revoke consent (for testing or explicit revocation)."""
        async with _lock:
            if customer_id in _consents:
                if consent_type.value in _consents[customer_id]:
                    del _consents[customer_id][consent_type.value]
                    return True
            return False

    async def clear_all_consents(self, customer_id: str) -> None:
        """Clear all consents for a customer (for testing)."""
        async with _lock:
            if customer_id in _consents:
                del _consents[customer_id]


# Module-level convenience functions

async def record_consent(
    customer_id: str,
    consent_type: ConsentType,
    ip_address: str,
    user_agent: str = "Unknown",
    legal_text_version: str = "v2026.1"
) -> ConsentRecord:
    """Record FCRA consent."""
    manager = ConsentManager()
    return await manager.record_consent(
        customer_id, consent_type, ip_address, user_agent, legal_text_version
    )


async def check_consent(
    customer_id: str,
    consent_type: ConsentType = ConsentType.SOFT_PULL
) -> ConsentCheckResult:
    """Check if valid consent exists."""
    manager = ConsentManager()
    return await manager.check_consent_valid(customer_id, consent_type)


async def get_active_consent(
    customer_id: str,
    consent_type: ConsentType = ConsentType.SOFT_PULL
) -> Optional[ConsentRecord]:
    """Get active consent record."""
    manager = ConsentManager()
    return await manager.get_active_consent(customer_id, consent_type)


def get_consent_text(
    version: str = "v2026.1",
    dealer_name: str = "Mini-Lakebed Demo Dealer"
) -> str:
    """Get consent legal text."""
    manager = ConsentManager()
    return manager.get_consent_legal_text(version, dealer_name)
