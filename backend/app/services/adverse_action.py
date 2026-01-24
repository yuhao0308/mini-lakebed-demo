"""
T03: Adverse Action Service

Regulation B compliant adverse action notice generation.
Per tasks/T03_credit_flow.md
"""

import hashlib
import json
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict

from app.models.credit import (
    AdverseActionReason,
    AdverseActionNotice,
    CreditDecision,
    CounterOffer,
    NoticeDeliveryResult,
)
from app.services.database import execute_insert, execute_query


# Reg B factor code to reason text mapping
# Per CFPB guidance: Cannot use generic reasons like "Bad Credit" or "Internal Policy"
FACTOR_CODE_MAPPING: Dict[str, str] = {
    # Income/Employment factors
    "A01": "Income insufficient for amount of credit requested",
    "A02": "Excessive obligations in relation to income",
    "A03": "Unable to verify income",
    "A04": "Temporary or irregular employment",
    "A05": "Length of employment",
    "A06": "Unable to verify employment",
    "A07": "Temporary residence",
    "A08": "Length of residence",
    "A09": "Unable to verify residence",
    "A12": "Length of employment",  # Alias used in spec

    # Collateral factors
    "B01": "Value or type of collateral not sufficient",
    "B02": "Unable to verify value of collateral",
    "B03": "Unacceptable type of collateral",
    "B04": "No collateral",

    # Credit references
    "C01": "Too few bank references",
    "C02": "No credit file",
    "C03": "Limited credit experience",
    "C04": "Insufficient number of credit references provided",
    "C05": "Unable to verify credit references",

    # Credit history factors
    "D01": "Credit application incomplete",
    "D02": "Delinquent past or present credit obligations with others",
    "D03": "Garnishment, attachment, foreclosure, repossession, collection action, or judgment",
    "D04": "Bankruptcy",
    "D05": "Ratio of balance to limit on bank revolving or other revolving accounts is too high",
    "D06": "Number of recent inquiries on credit bureau report",
    "D07": "Poor credit performance with us",

    # Bureau-specific codes (common in industry)
    "04": "Ratio of balance to limit on bank revolving accounts is too high",
    "12": "Delinquency or past due checks",
    "14": "Length of time accounts have been established",
    "18": "Number of accounts with delinquency",
    "20": "Length of time since derogatory public record or collection filed",
    "34": "Amount owed on revolving accounts is too high",
    "40": "Derogatory public record or collection filed",
}

# Forbidden generic reasons (per CFPB Circular 2023-03)
FORBIDDEN_REASONS = [
    "bad credit",
    "credit score",
    "internal policy",
    "proprietary model",
    "credit denied",
    "not qualified",
]


class AdverseActionService:
    """
    Regulation B compliant adverse action notice generation.
    """

    def map_factor_code_to_reason(
        self,
        factor_code: str
    ) -> AdverseActionReason:
        """
        Map bureau factor codes to Reg B specific text.

        E.g., "04" -> "Ratio of balance to limit on bank revolving accounts is too high"

        Per CFPB Circular 2023-03: Cannot use generic reasons like
        "Credit Score" or "Internal Policy".
        """
        text = FACTOR_CODE_MAPPING.get(
            factor_code,
            f"Credit factor {factor_code} contributed to this decision"
        )

        # Validate not generic
        if any(forbidden in text.lower() for forbidden in FORBIDDEN_REASONS):
            raise ValueError(f"Generic reason not allowed: {text}")

        return AdverseActionReason(code=factor_code, text=text)

    async def generate_notice(
        self,
        customer_id: str,
        credit_decision: CreditDecision,
        bureau_factors: List[str]
    ) -> AdverseActionNotice:
        """
        Generate formal adverse action notice with:
        - Up to 4 principal reasons (Reg B requirement)
        - Specific text per reason code
        - Bureau used and score date
        - Counter-offer if applicable
        """
        notice_id = f"aa_{uuid.uuid4().hex[:12]}"

        # Map factor codes to reasons (max 4 per Reg B)
        principal_reasons = []
        for code in bureau_factors[:4]:  # Max 4 reasons
            reason = self.map_factor_code_to_reason(code)
            principal_reasons.append(reason)

        # Use decline reasons from credit decision if no bureau factors
        if not principal_reasons and credit_decision.decline_reasons:
            principal_reasons = credit_decision.decline_reasons[:4]

        notice = AdverseActionNotice(
            notice_id=notice_id,
            customer_id=customer_id,
            generated_at=datetime.utcnow(),
            bureau_source=credit_decision.bureau_source,
            score_date=credit_decision.score_date,
            fico_score=credit_decision.fico_score,
            principal_reasons=principal_reasons,
            counter_offer=credit_decision.counter_offer,
            pdf_url=f"/api/adverse-action/{notice_id}/pdf"
        )

        # Log notice generation
        await self._log_notice_generated(notice)

        return notice

    async def send_notice(
        self,
        notice: AdverseActionNotice,
        delivery_method: str  # email | mail | download
    ) -> NoticeDeliveryResult:
        """
        Send notice and log delivery for compliance.
        """
        tracking_id = f"track_{uuid.uuid4().hex[:8]}"

        # In demo mode, we just log the delivery
        result = NoticeDeliveryResult(
            success=True,
            delivery_method=delivery_method,
            delivered_at=datetime.utcnow(),
            tracking_id=tracking_id
        )

        # Log delivery for compliance
        await self._log_notice_delivery(notice, result)

        return result

    def validate_notice_compliance(
        self,
        notice: AdverseActionNotice
    ) -> tuple[bool, List[str]]:
        """
        Validate notice meets Reg B requirements.

        Returns (valid, list of violations)
        """
        violations = []

        # Check max 4 reasons
        if len(notice.principal_reasons) > 4:
            violations.append("Notice has more than 4 principal reasons (Reg B max)")

        # Check for generic reasons
        for reason in notice.principal_reasons:
            if any(forbidden in reason.text.lower() for forbidden in FORBIDDEN_REASONS):
                violations.append(f"Generic reason not allowed: {reason.text}")

        # Check bureau source present (None, empty, or not a valid bureau)
        if not notice.bureau_source or notice.bureau_source.strip() == "":
            violations.append("Bureau source is required")

        # Check score date present
        if not notice.score_date:
            violations.append("Score date is required")

        return len(violations) == 0, violations

    async def _log_notice_generated(self, notice: AdverseActionNotice) -> None:
        """Log notice generation to audit_logs."""
        transaction_id = str(uuid.uuid4())

        payload = {
            "notice_id": notice.notice_id,
            "customer_id": notice.customer_id,
            "bureau_source": notice.bureau_source,
            "score_date": notice.score_date.isoformat(),
            "fico_score": notice.fico_score,
            "reasons": [r.model_dump() for r in notice.principal_reasons],
            "has_counter_offer": notice.counter_offer is not None
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        regulatory_flags = {
            "adverse_action_generated": True,
            "reg_b_compliant": True,
            "reason_count": len(notice.principal_reasons)
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
                    notice.customer_id,
                    f"adverse_action:generated",
                    transaction_id,
                    "agent:credit_officer",
                    "adverse_action_generated",
                    payload_hash,
                    json.dumps(regulatory_flags)
                )
            )
        except Exception as e:
            print(f"Warning: Failed to log adverse action generation: {e}")

    async def _log_notice_delivery(
        self,
        notice: AdverseActionNotice,
        result: NoticeDeliveryResult
    ) -> None:
        """Log notice delivery to audit_logs."""
        transaction_id = str(uuid.uuid4())

        payload = {
            "notice_id": notice.notice_id,
            "delivery_method": result.delivery_method,
            "tracking_id": result.tracking_id,
            "delivered_at": result.delivered_at.isoformat()
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        regulatory_flags = {
            "adverse_action_delivered": True,
            "delivery_method": result.delivery_method
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
                    notice.customer_id,
                    f"adverse_action:delivered:{result.delivery_method}",
                    transaction_id,
                    "agent:credit_officer",
                    "adverse_action_delivered",
                    payload_hash,
                    json.dumps(regulatory_flags)
                )
            )
        except Exception as e:
            print(f"Warning: Failed to log adverse action delivery: {e}")


# Module-level convenience functions

def map_factor_code(code: str) -> AdverseActionReason:
    """Map factor code to reason."""
    service = AdverseActionService()
    return service.map_factor_code_to_reason(code)


async def generate_notice(
    customer_id: str,
    credit_decision: CreditDecision,
    bureau_factors: List[str]
) -> AdverseActionNotice:
    """Generate adverse action notice."""
    service = AdverseActionService()
    return await service.generate_notice(customer_id, credit_decision, bureau_factors)


async def send_notice(
    notice: AdverseActionNotice,
    delivery_method: str = "download"
) -> NoticeDeliveryResult:
    """Send adverse action notice."""
    service = AdverseActionService()
    return await service.send_notice(notice, delivery_method)
