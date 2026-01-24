"""
T03: Consent Router

API endpoint for FCRA consent submission.
Per tasks/T03_credit_flow.md
"""

from typing import Optional
from fastapi import APIRouter, Header, Request

from app.models.credit import (
    ConsentType,
    ConsentRequest,
    ConsentResponse,
)
from app.services.consent_manager import ConsentManager, get_consent_text

router = APIRouter()


@router.post("/consent", response_model=ConsentResponse)
async def submit_consent(
    request: ConsentRequest,
    http_request: Request,
    x_forwarded_for: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None, alias="User-Agent")
):
    """
    Record FCRA consent submission.

    Request:
    {
        "customer_id": "uuid",
        "consent_type": "soft_pull",
        "legal_text_version": "v2026.1"
    }

    Response:
    {
        "success": true,
        "consent_id": "consent_xxx",
        "expires_at": "2026-02-22T..."
    }
    """
    # Get IP address from X-Forwarded-For or client host
    ip_address = x_forwarded_for or http_request.client.host or "unknown"

    # Get user agent
    ua = user_agent or "Unknown"

    try:
        manager = ConsentManager()
        record = await manager.record_consent(
            customer_id=request.customer_id,
            consent_type=request.consent_type,
            ip_address=ip_address,
            user_agent=ua,
            legal_text_version=request.legal_text_version
        )

        return ConsentResponse(
            success=True,
            consent_id=record.consent_id,
            expires_at=record.expires_at
        )

    except Exception as e:
        return ConsentResponse(
            success=False,
            error=str(e)
        )


@router.get("/consent/legal-text")
async def get_legal_text(
    version: str = "v2026.1",
    dealer_name: str = "Mini-Lakebed Demo Dealer"
):
    """
    Get the FCRA consent legal text for display.
    """
    return {
        "version": version,
        "text": get_consent_text(version, dealer_name),
        "dealer_name": dealer_name
    }


@router.get("/consent/check/{customer_id}")
async def check_consent(customer_id: str):
    """
    Check if customer has valid FCRA consent.
    """
    manager = ConsentManager()
    result = await manager.check_consent_valid(customer_id, ConsentType.SOFT_PULL)

    return {
        "customer_id": customer_id,
        "valid": result.valid,
        "requires_consent": result.requires_consent,
        "message": result.message
    }
