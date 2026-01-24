"""
Payments router for payment estimates.

⚠️ All calculations are DETERMINISTIC - the LLM never generates payment amounts.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from app.models.schemas import (
    PaymentRequest, PaymentResponse, PaymentErrorResponse,
    PaymentEstimate, PaymentAudit, CalculationTrace
)
from app.services.database import execute_one
from app.services.calculator import estimate_payment

router = APIRouter()

DISCLAIMER = "⚠️ DEMO ONLY: Synthetic lender rules for demonstration purposes. Not a commitment to lend."


@router.post("/estimate_payment")
async def create_payment_estimate(
    request: PaymentRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Calculate a payment estimate using approved lender rules.

    This endpoint uses DETERMINISTIC calculation - the LLM never generates amounts.
    Every response includes rule_id citation and full calculation trace.

    T02: SB 766 compliance check - offering price must be disclosed first.
    """
    from app.services.compliance_sentinel import ComplianceSentinel

    # Get vehicle price
    vehicle = await execute_one(
        "SELECT * FROM inventory WHERE id = ?",
        (request.vehicle_id,)
    )

    # T02: SB 766 Compliance Check (if session provided)
    if x_session_id:
        compliance = ComplianceSentinel()
        check = await compliance.check_payment_allowed(x_session_id, request.vehicle_id)

        if not check.allowed:
            return {
                "success": False,
                "error": {
                    "code": check.violation.code if check.violation else "COMPLIANCE_ERROR",
                    "message": check.violation.message if check.violation else "Compliance check failed",
                    "details": {
                        "regulation": check.violation.regulation if check.violation else None,
                        "required_action": check.required_action,
                        "blocked_action": check.violation.blocked_action if check.violation else None
                    }
                }
            }
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if vehicle["status"] != "available":
        raise HTTPException(
            status_code=422, 
            detail=f"Vehicle is {vehicle['status']}, not available for purchase"
        )
    
    vehicle_price = vehicle["price"]
    
    # Validate down payment
    if request.down_payment >= vehicle_price:
        raise HTTPException(
            status_code=422,
            detail="Down payment must be less than vehicle price"
        )
    
    # Calculate payment
    try:
        result = await estimate_payment(
            vehicle_price=vehicle_price,
            down_payment=request.down_payment,
            fico_score=request.fico_estimate,
            term_months=request.term_months
        )
    except ValueError as e:
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {}
            }
        }
    
    if not result:
        # No matching rule found
        return {
            "success": False,
            "error": {
                "code": "NO_MATCHING_RULE",
                "message": "No lender rules match the provided credit profile and term.",
                "details": {
                    "fico_estimate": request.fico_estimate,
                    "term_months": request.term_months,
                    "credit_tier": request.credit_tier.value,
                    "suggestion": "Try adjusting the credit tier or loan term."
                }
            }
        }
    
    # Build response with full audit trail
    return PaymentResponse(
        success=True,
        estimate=PaymentEstimate(
            monthly_payment=result.monthly_payment,
            apr=result.apr,
            term_months=result.term_months,
            principal=result.principal,
            total_interest=result.total_interest,
            total_cost=result.total_cost
        ),
        audit=PaymentAudit(
            rule_id=result.rule_id,
            lender=result.lender_name,
            matched_criteria={
                "fico_score": request.fico_estimate,
                "term_months": request.term_months,
                "ltv": result.ltv
            },
            calculation_trace=CalculationTrace(
                vehicle_price=vehicle_price,
                down_payment=request.down_payment,
                principal=result.principal,
                monthly_rate=round(result.apr / 100 / 12, 6)
            )
        ),
        disclaimer=DISCLAIMER
    )


@router.get("/available_terms/{fico_score}")
async def get_available_terms(fico_score: int):
    """
    Get available loan terms for a given FICO score.
    
    Returns list of available terms with their APRs.
    """
    from app.services.database import execute_query
    
    rules = await execute_query("""
        SELECT DISTINCT 
            credit_tier,
            min_term_months,
            max_term_months,
            base_apr,
            max_ltv,
            rule_id
        FROM lender_rules
        WHERE ? BETWEEN min_fico AND max_fico
          AND is_demo = 1
        ORDER BY base_apr ASC
    """, (fico_score,))
    
    if not rules:
        return {
            "fico_score": fico_score,
            "available_rules": [],
            "message": "No rules available for this credit score range."
        }
    
    return {
        "fico_score": fico_score,
        "available_rules": rules,
        "disclaimer": DISCLAIMER
    }
