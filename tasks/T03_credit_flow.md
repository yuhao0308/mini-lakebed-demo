# T03: Credit Flow (FCRA / Reg B)

**Priority:** High
**Status:** Not Started
**Depends On:** T01 (Data Foundation)
**Blocked By:** T01

---

## Objective

Implement the Credit_Officer agent to handle soft-pull consent, credit tier assignment, and Regulation B adverse action notice generation. This enables the "Soft-Pull Handshake" flow from the demo script.

---

## Spec References

| Spec File | Section | Requirement |
|-----------|---------|-------------|
| `02_strategic_blueprint.md` | §3.1 Agent 5: The Credit_Officer | Decision engine for credit tiering + adverse action |
| `02_strategic_blueprint.md` | §4 User Story 4: Soft-Pull Consent Handshake | "Written instructions" UI Card with FCRA language |
| `02_strategic_blueprint.md` | §4 User Story 5: Identity Verification | Red Flags Rule - address mismatch detection |
| `02_strategic_blueprint.md` | §4 User Story 8: Adverse Action Explanation | Specific Reg B reason codes, not generic "bad credit" |
| `02_strategic_blueprint.md` | §4 User Story 9: Counter-Offer | Conditional approval with alternative terms |
| `02_strategic_blueprint.md` | §5 Demo Script Scene 2 | Soft-pull consent flow with UI card |
| `02_strategic_blueprint.md` | §5 Demo Script Scene 4 | Adverse action with specific reasons |
| `03_implementation_dummy_data_plan.md` | §0.3.2 Regulation B | Specific principal reasons (up to 4) for denials |
| `03_implementation_dummy_data_plan.md` | §0.3.3 FCRA | Soft pull requires "written instruction" with timestamp, IP |
| `03_implementation_dummy_data_plan.md` | §1.1 CustomerProfile | `fcra_consent_log[]` with consent_id, type, granted_at, ip_address, expires_at |
| `03_implementation_dummy_data_plan.md` | §1.4 ComplianceLog | `denial_reasons[]` with Reg B codes |
| `03_implementation_dummy_data_plan.md` | §4.3 Regulation B: Adverse Action Logic | Map factor codes to specific text |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/services/credit_officer.py` | Main credit decision engine |
| `backend/app/services/consent_manager.py` | FCRA consent tracking and validation |
| `backend/app/services/adverse_action.py` | Reg B notice generation |
| `backend/app/models/credit.py` | Pydantic models for credit flow |
| `backend/app/routers/consent.py` | API endpoint for consent submission |
| `backend/tests/test_credit_officer.py` | Unit tests for credit decisions |
| `backend/tests/test_fcra_consent.py` | Tests for consent flow |
| `backend/tests/test_adverse_action.py` | Tests for adverse action generation |
| `frontend/src/components/Consent/SoftPullCard.tsx` | FCRA consent UI component |
| `frontend/src/components/Consent/SoftPullCard.css` | Styling for consent card |

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/routers/chat.py` | Add credit prequalification intent handling |
| `backend/app/services/llm.py` | Add `Intent.CREDIT_PREQUALIFICATION` |
| `backend/app/services/session_context.py` | Add `credit_status`, `fcra_consent` fields |
| `backend/app/main.py` | Register consent router |
| `frontend/src/components/Chat/ChatPane.tsx` | Render SoftPullCard when appropriate |
| `frontend/src/services/api.ts` | Add consent submission API |

---

## Implementation Specifications

### credit_officer.py

```python
class CreditOfficer:
    """
    The "Underwriter" agent - handles credit decisions with explainability.

    Responsibilities:
    - Validate FCRA consent before any credit check
    - Assign credit tier based on FICO score
    - Generate Reg B compliant adverse action notices
    - Provide counter-offers for conditional approvals
    """

    async def check_consent_valid(
        self,
        customer_id: str
    ) -> ConsentCheckResult:
        """
        Verify active FCRA consent exists for soft pull.

        Returns:
            ConsentCheckResult with valid=True or requires_consent=True
        """

    async def assign_credit_tier(
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
        - Decline: <600
        """

    async def evaluate_application(
        self,
        customer_id: str,
        vehicle_id: int,
        requested_terms: RequestedTerms
    ) -> CreditDecision:
        """
        Full credit evaluation returning approval, conditional, or decline.
        """

    async def generate_counter_offer(
        self,
        original_request: RequestedTerms,
        lender_constraints: LenderConstraints
    ) -> Optional[CounterOffer]:
        """
        Calculate alternative terms that would result in approval.
        E.g., higher down payment to meet LTV requirements.
        """
```

### consent_manager.py

```python
class ConsentManager:
    """
    FCRA consent tracking with full audit trail.
    """

    async def record_consent(
        self,
        customer_id: str,
        consent_type: ConsentType,  # soft_pull | hard_pull
        ip_address: str,
        user_agent: str,
        legal_text_version: str
    ) -> ConsentRecord:
        """
        Record FCRA consent with all required metadata.

        Consent expires after 30 days per spec.
        """

    async def get_active_consent(
        self,
        customer_id: str,
        consent_type: ConsentType
    ) -> Optional[ConsentRecord]:
        """
        Get active (non-expired) consent for customer.
        """

    def get_consent_legal_text(
        self,
        version: str = "v2026.1"
    ) -> str:
        """
        Return the specific legal text for consent UI.

        Per spec: "I understand that by clicking 'Submit', I am providing
        'written instructions' under the FCRA authorizing [Dealer] to obtain
        personal credit information... solely for pre-qualification.
        This will not affect my credit score."
        """
```

### adverse_action.py

```python
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

    async def send_notice(
        self,
        notice: AdverseActionNotice,
        delivery_method: str  # email | mail | download
    ) -> NoticeDeliveryResult:
        """
        Send notice and log delivery for compliance.
        """
```

### Credit Models (credit.py)

```python
class ConsentType(str, Enum):
    SOFT_PULL = "soft_pull"
    HARD_PULL = "hard_pull"

class ConsentRecord(BaseModel):
    consent_id: str
    customer_id: str
    consent_type: ConsentType
    granted_at: datetime
    ip_address: str
    user_agent: str
    legal_text_version: str
    expires_at: datetime

class CreditTier(str, Enum):
    SUPER_PRIME = "super_prime"  # 750+
    PRIME = "prime"              # 700-749
    NEAR_PRIME = "near_prime"    # 650-699
    SUBPRIME = "subprime"        # 600-649
    DECLINE = "decline"          # <600

class CreditDecision(BaseModel):
    decision: str  # approved | conditional | declined
    tier: CreditTier
    approved_terms: Optional[ApprovedTerms] = None
    conditions: Optional[List[str]] = None  # Required stips
    decline_reasons: Optional[List[AdverseActionReason]] = None
    counter_offer: Optional[CounterOffer] = None

class AdverseActionReason(BaseModel):
    code: str  # e.g., "A01"
    text: str  # e.g., "Income insufficient for amount of credit requested"

class AdverseActionNotice(BaseModel):
    notice_id: str
    customer_id: str
    generated_at: datetime
    bureau_source: str  # Equifax | Experian | TransUnion
    score_date: date
    principal_reasons: List[AdverseActionReason]  # Max 4
    counter_offer: Optional[CounterOffer] = None
    pdf_url: Optional[str] = None

class CounterOffer(BaseModel):
    required_down_payment: float
    approved_apr: float
    approved_term: int
    message: str  # Human-readable explanation
```

---

## API Endpoints

### POST /api/consent

```python
@router.post("/consent")
async def submit_consent(
    request: ConsentRequest,
    x_forwarded_for: str = Header(None)
) -> ConsentResponse:
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
```

---

## Frontend: SoftPullCard Component

Per `02_strategic_blueprint.md` §5 Demo Scene 2:

```tsx
// SoftPullCard.tsx
interface SoftPullCardProps {
  onConsent: () => void;
  onCancel: () => void;
  dealerName: string;
}

const SoftPullCard: React.FC<SoftPullCardProps> = ({
  onConsent,
  onCancel,
  dealerName
}) => {
  return (
    <div className="soft-pull-card">
      <h3>Credit Pre-Qualification</h3>
      <p className="consent-text">
        I understand that by clicking 'Submit', I am providing
        'written instructions' under the FCRA authorizing {dealerName}
        to obtain personal credit information from one or more consumer
        reporting agencies solely for pre-qualification purposes.
        <strong> This will not affect my credit score.</strong>
      </p>
      <div className="actions">
        <button className="primary" onClick={onConsent}>
          I Agree
        </button>
        <button className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
};
```

---

## Acceptance Tests

### Test File: `backend/tests/test_credit_officer.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T03-01 | `test_tier_super_prime_750` | FICO 750 → `super_prime` |
| T03-02 | `test_tier_prime_720` | FICO 720 → `prime` |
| T03-03 | `test_tier_near_prime_670` | FICO 670 → `near_prime` |
| T03-04 | `test_tier_subprime_620` | FICO 620 → `subprime` |
| T03-05 | `test_tier_decline_580` | FICO 580 → `decline` |
| T03-06 | `test_evaluation_requires_consent` | Evaluation without consent returns `requires_consent=True` |
| T03-07 | `test_evaluation_with_consent` | Evaluation with valid consent proceeds |
| T03-08 | `test_counter_offer_ltv_violation` | LTV > max generates counter-offer with higher down payment |

### Test File: `backend/tests/test_fcra_consent.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T03-09 | `test_consent_recorded_with_ip` | Consent record includes IP address |
| T03-10 | `test_consent_recorded_with_timestamp` | Consent record includes precise timestamp |
| T03-11 | `test_consent_expires_30_days` | Consent `expires_at` is 30 days from `granted_at` |
| T03-12 | `test_expired_consent_invalid` | Consent granted 31 days ago returns `valid=False` |
| T03-13 | `test_consent_legal_text_version` | Consent record includes `legal_text_version` |
| T03-14 | `test_consent_audit_logged` | Consent creates audit log with `event_type=soft_pull_consent` |

### Test File: `backend/tests/test_adverse_action.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T03-15 | `test_factor_code_A01_mapping` | Code "A01" → "Income insufficient for amount of credit requested" |
| T03-16 | `test_factor_code_A12_mapping` | Code "A12" → "Length of employment" |
| T03-17 | `test_notice_max_4_reasons` | Notice contains at most 4 principal reasons |
| T03-18 | `test_notice_no_generic_reasons` | Notice does not contain "Bad Credit" or "Internal Policy" |
| T03-19 | `test_notice_includes_bureau_source` | Notice includes bureau name (Equifax/Experian/TransUnion) |
| T03-20 | `test_notice_includes_score_date` | Notice includes date credit was pulled |
| T03-21 | `test_notice_with_counter_offer` | Conditional decline includes counter-offer terms |
| T03-22 | `test_notice_delivery_logged` | Notice delivery creates compliance log entry |

---

## Demo Script Alignment

### Scene 2: Soft-Pull Handshake

**User:** "Can I get approved?"

**Expected Flow:**
1. `Conversationalist` detects `Intent: Credit_Prequalification`
2. `Compliance_Sentinel` blocks: "Cannot quote specific rate without Permissible Purpose"
3. System triggers `UI_Card: Soft_Pull_Consent`
4. User clicks "I Agree"
5. `ConsentManager` logs consent with timestamp, IP
6. `CreditOfficer` calls mock 700Credit API
7. Result: Score 680 (Tier 2), Factor: High_Utilization
8. `Fin_Calc_Solver` ingests rate sheet for Tier 2

### Scene 4: Adverse Action

**Scenario:** User has FICO 550 (decline threshold)

**Expected Flow:**
1. `CreditOfficer` returns `decision: declined`
2. `AdverseActionService` maps factor codes:
   - "04" → "Ratio of balance to limit on bank revolving accounts is too high"
   - "12" → "Delinquency or past due checks"
3. Response includes specific reasons (NOT "Bad Credit")
4. Counter-offer calculated: "$3,000 down, 48-month term"
5. PDF download link provided

---

## Definition of Done

- [ ] `CreditOfficer` service created with tier assignment and evaluation
- [ ] `ConsentManager` service created with FCRA logging
- [ ] `AdverseActionService` created with Reg B reason mapping
- [ ] All Pydantic models created
- [ ] `/api/consent` endpoint functional
- [ ] `SoftPullCard.tsx` component created
- [ ] Chat integration renders consent card when appropriate
- [ ] All 22 acceptance tests pass
- [ ] Demo script Scenes 2 and 4 work as specified
- [ ] No regressions in existing tests
