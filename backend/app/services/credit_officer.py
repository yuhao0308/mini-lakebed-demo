"""
T03: Credit Officer Service

The "Underwriter" agent - handles credit decisions with explainability.
Per tasks/T03_credit_flow.md
"""

from datetime import date
from typing import Optional, List

from app.models.credit import (
    ConsentType,
    ConsentCheckResult,
    CreditTier,
    CreditTierResult,
    CreditDecision,
    RequestedTerms,
    ApprovedTerms,
    AdverseActionReason,
    CounterOffer,
    LenderConstraints,
)
from app.services.consent_manager import ConsentManager
from app.services.adverse_action import AdverseActionService
from app.services.calculator import select_lender_rule, calculate_monthly_payment
from app.services.database import execute_one


# Credit tier boundaries
TIER_BOUNDARIES = {
    CreditTier.SUPER_PRIME: (750, 850),
    CreditTier.PRIME: (700, 749),
    CreditTier.NEAR_PRIME: (650, 699),
    CreditTier.SUBPRIME: (600, 649),
    CreditTier.DEEP_SUBPRIME: (550, 599),
    CreditTier.DECLINE: (300, 549),
}


class CreditOfficer:
    """
    The "Underwriter" agent - handles credit decisions with explainability.

    Responsibilities:
    - Validate FCRA consent before any credit check
    - Assign credit tier based on FICO score
    - Generate Reg B compliant adverse action notices
    - Provide counter-offers for conditional approvals
    """

    def __init__(self):
        self.consent_manager = ConsentManager()
        self.adverse_action_service = AdverseActionService()

    async def check_consent_valid(
        self,
        customer_id: str
    ) -> ConsentCheckResult:
        """
        Verify active FCRA consent exists for soft pull.

        Returns:
            ConsentCheckResult with valid=True or requires_consent=True
        """
        return await self.consent_manager.check_consent_valid(
            customer_id, ConsentType.SOFT_PULL
        )

    def assign_credit_tier(
        self,
        fico_score: int
    ) -> CreditTierResult:
        """
        Map FICO score to credit tier.

        Tiers (per spec):
        - Super Prime: 750+
        - Prime: 700-749
        - Near Prime: 650-699
        - Subprime: 600-649
        - Deep Subprime: 550-599
        - Decline: <550
        """
        tier = CreditTier.DECLINE

        if fico_score >= 750:
            tier = CreditTier.SUPER_PRIME
        elif fico_score >= 700:
            tier = CreditTier.PRIME
        elif fico_score >= 650:
            tier = CreditTier.NEAR_PRIME
        elif fico_score >= 600:
            tier = CreditTier.SUBPRIME
        elif fico_score >= 550:
            tier = CreditTier.DEEP_SUBPRIME
        else:
            tier = CreditTier.DECLINE

        return CreditTierResult(
            tier=tier,
            fico_score=fico_score,
            tier_boundaries={
                "super_prime": "750+",
                "prime": "700-749",
                "near_prime": "650-699",
                "subprime": "600-649",
                "deep_subprime": "550-599",
                "decline": "<550"
            }
        )

    async def evaluate_application(
        self,
        customer_id: str,
        vehicle_id: int,
        fico_score: int,
        requested_terms: RequestedTerms
    ) -> CreditDecision:
        """
        Full credit evaluation returning approval, conditional, or decline.
        """
        # Check consent first
        consent_check = await self.check_consent_valid(customer_id)
        if not consent_check.valid:
            return CreditDecision(
                decision="requires_consent",
                tier=CreditTier.DECLINE,
                fico_score=fico_score,
                conditions=["FCRA consent required before credit evaluation"]
            )

        # Assign tier
        tier_result = self.assign_credit_tier(fico_score)

        # Decline for very low scores
        if tier_result.tier == CreditTier.DECLINE:
            return CreditDecision(
                decision="declined",
                tier=tier_result.tier,
                fico_score=fico_score,
                decline_reasons=[
                    AdverseActionReason(
                        code="C03",
                        text="Limited credit experience"
                    ),
                    AdverseActionReason(
                        code="D02",
                        text="Delinquent past or present credit obligations with others"
                    ),
                ],
                bureau_source="Experian",
                score_date=date.today()
            )

        # Calculate LTV
        loan_amount = requested_terms.vehicle_price - requested_terms.down_payment
        ltv = loan_amount / requested_terms.vehicle_price

        # Find matching lender rule
        rule = await select_lender_rule(
            fico_score,
            requested_terms.term_months,
            ltv
        )

        if not rule:
            # No rule matches - try to generate counter-offer
            counter_offer = await self.generate_counter_offer(
                requested_terms,
                LenderConstraints(
                    max_ltv=1.20,  # 120% max LTV
                    max_term=72,
                    min_down_payment=requested_terms.vehicle_price * 0.10,  # 10% min
                    apr=self._get_base_apr_for_tier(tier_result.tier)
                ),
                fico_score
            )

            if counter_offer:
                return CreditDecision(
                    decision="conditional",
                    tier=tier_result.tier,
                    fico_score=fico_score,
                    conditions=[
                        f"Increase down payment to ${counter_offer.required_down_payment:,.0f}",
                        f"Maximum term: {counter_offer.approved_term} months"
                    ],
                    counter_offer=counter_offer,
                    bureau_source="Experian",
                    score_date=date.today()
                )

            return CreditDecision(
                decision="declined",
                tier=tier_result.tier,
                fico_score=fico_score,
                decline_reasons=[
                    AdverseActionReason(
                        code="B01",
                        text="Value or type of collateral not sufficient"
                    ),
                ],
                bureau_source="Experian",
                score_date=date.today()
            )

        # Approved - calculate terms
        principal = loan_amount + rule.get('doc_fee', 85)
        monthly_payment = calculate_monthly_payment(
            principal, rule['base_apr'], requested_terms.term_months
        )

        return CreditDecision(
            decision="approved",
            tier=tier_result.tier,
            fico_score=fico_score,
            approved_terms=ApprovedTerms(
                principal=principal,
                apr=rule['base_apr'],
                term_months=requested_terms.term_months,
                monthly_payment=monthly_payment,
                lender_name=rule['lender_name'],
                rule_id=rule['rule_id']
            ),
            bureau_source="Experian",
            score_date=date.today()
        )

    async def generate_counter_offer(
        self,
        original_request: RequestedTerms,
        lender_constraints: LenderConstraints,
        fico_score: int
    ) -> Optional[CounterOffer]:
        """
        Calculate alternative terms that would result in approval.
        E.g., higher down payment to meet LTV requirements.
        """
        vehicle_price = original_request.vehicle_price

        # Calculate required down payment to meet max LTV
        max_loan = vehicle_price * lender_constraints.max_ltv
        current_loan = vehicle_price - original_request.down_payment

        if current_loan > max_loan:
            # Need higher down payment
            required_down = vehicle_price - max_loan
            if required_down < 0:
                required_down = 0

            # Use minimum down payment if calculated is too low
            if required_down < lender_constraints.min_down_payment:
                required_down = lender_constraints.min_down_payment

            # Calculate new loan and payment
            new_loan = vehicle_price - required_down + 85  # Include doc fee
            term = min(original_request.term_months, lender_constraints.max_term)

            monthly_payment = calculate_monthly_payment(
                new_loan, lender_constraints.apr, term
            )

            return CounterOffer(
                required_down_payment=required_down,
                approved_apr=lender_constraints.apr,
                approved_term=term,
                monthly_payment=monthly_payment,
                message=(
                    f"We can approve you with a down payment of ${required_down:,.0f} "
                    f"at {lender_constraints.apr}% APR for {term} months. "
                    f"Your monthly payment would be ${monthly_payment:,.2f}."
                )
            )

        return None

    def _get_base_apr_for_tier(self, tier: CreditTier) -> float:
        """Get base APR for credit tier (for counter-offers)."""
        apr_map = {
            CreditTier.SUPER_PRIME: 4.99,
            CreditTier.PRIME: 6.49,
            CreditTier.NEAR_PRIME: 8.99,
            CreditTier.SUBPRIME: 12.99,
            CreditTier.DEEP_SUBPRIME: 17.99,
            CreditTier.DECLINE: 24.99,
        }
        return apr_map.get(tier, 12.99)


# Module-level convenience functions

def get_credit_tier(fico_score: int) -> CreditTierResult:
    """Get credit tier for FICO score."""
    officer = CreditOfficer()
    return officer.assign_credit_tier(fico_score)


async def check_consent(customer_id: str) -> ConsentCheckResult:
    """Check if customer has valid consent."""
    officer = CreditOfficer()
    return await officer.check_consent_valid(customer_id)


async def evaluate_credit(
    customer_id: str,
    vehicle_id: int,
    fico_score: int,
    requested_terms: RequestedTerms
) -> CreditDecision:
    """Evaluate credit application."""
    officer = CreditOfficer()
    return await officer.evaluate_application(
        customer_id, vehicle_id, fico_score, requested_terms
    )
