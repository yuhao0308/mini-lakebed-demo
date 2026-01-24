# T02: Core Compliance (SB 766 / CARS Act)

**Priority:** High
**Status:** Not Started
**Depends On:** T01 (Data Foundation)
**Blocked By:** T01

---

## Objective

Implement the Compliance_Sentinel agent to enforce California SB 766 "Offering Price" disclosure rules and CARS Act "Valueless Add-on" prohibitions. This agent intercepts requests and blocks non-compliant flows.

---

## Spec References

| Spec File | Section | Requirement |
|-----------|---------|-------------|
| `02_strategic_blueprint.md` | §3.1 Agent 4: The Compliance_Sentinel | Classifier + Rules Engine for regulatory scanning |
| `02_strategic_blueprint.md` | §4 User Story 1: Total Price Disclosure | "Cannot quote payment without Offering Price disclosure" |
| `02_strategic_blueprint.md` | §4 User Story 2: Valueless Add-on Prevention | Block add-ons with no benefit to specific vehicle |
| `02_strategic_blueprint.md` | §5 Demo Script Scene 1 | "SB 766 Triggered. Offering Price must be disclosed clearly" |
| `03_implementation_dummy_data_plan.md` | §0.3.1 California SB 766 & SB 478 | `sb766_offering_price` = full cash price excluding only government charges |
| `03_implementation_dummy_data_plan.md` | §1.2 InventoryUnit | `add_ons[].compliance_check_passed` must be validated |
| `03_implementation_dummy_data_plan.md` | §2.2 Stage 2 | Valueless Product Check before pricing |
| `01_general_proposal.md` | §1.2 Regulatory Landscape | SB 766 requires "Offering Price" before monthly payment discussion |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/services/compliance_sentinel.py` | Main compliance enforcement service |
| `backend/app/services/disclosure_tracker.py` | Track which disclosures have been shown per session |
| `backend/app/models/compliance.py` | Pydantic models for compliance checks and violations |
| `backend/tests/test_compliance_sentinel.py` | Unit tests for compliance rules |
| `backend/tests/test_sb766_disclosure.py` | Integration tests for disclosure flow |
| `backend/tests/test_valueless_addons.py` | Tests for add-on validation |

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/routers/chat.py` | Intercept payment inquiries with compliance check |
| `backend/app/routers/payments.py` | Add disclosure verification before calculation |
| `backend/app/services/session_context.py` | Add `disclosures_shown` tracking |
| `backend/app/services/llm.py` | Add `Intent.PAYMENT_INQUIRY` detection |

---

## Implementation Specifications

### compliance_sentinel.py

```python
class ComplianceSentinel:
    """
    The "Guard" agent - enforces regulatory compliance in real-time.

    Responsibilities:
    - Block payment quotes without prior Offering Price disclosure (SB 766)
    - Validate add-ons have documented benefit for specific vehicle
    - Log all compliance events with payload hashes
    """

    async def check_payment_allowed(
        self,
        session_id: str,
        vehicle_id: int
    ) -> ComplianceCheckResult:
        """
        Verify that Offering Price has been disclosed before allowing payment quote.

        Returns:
            ComplianceCheckResult with allowed=True or violation details
        """

    async def validate_addon(
        self,
        vehicle: InventoryUnit,
        addon: AddOn
    ) -> AddOnValidationResult:
        """
        Check if add-on provides documented benefit for this specific vehicle.

        Rules:
        - If fuel_type='electric' and addon.name contains 'oil change' -> BLOCK
        - If addon.benefit_statement is None/empty -> BLOCK
        - If addon.compliance_check_passed is False -> BLOCK
        """

    async def enforce_offering_price_first(
        self,
        intent: Intent,
        session_context: SessionContext,
        vehicle_id: int
    ) -> Optional[ComplianceViolation]:
        """
        Core SB 766 enforcement logic.

        If intent is PAYMENT_INQUIRY and offering price not yet disclosed:
        Return ComplianceViolation forcing disclosure first.
        """
```

### disclosure_tracker.py

```python
class DisclosureTracker:
    """
    Track which regulatory disclosures have been presented per session.
    """

    def record_offering_price_shown(
        self,
        session_id: str,
        vehicle_id: int,
        offering_price: float,
        components: OfferingPriceComponents
    ) -> str:
        """
        Record that offering price was disclosed.
        Returns disclosure_id for audit trail.
        """

    def has_offering_price_been_shown(
        self,
        session_id: str,
        vehicle_id: int
    ) -> bool:
        """Check if offering price was disclosed for this vehicle in this session."""

    def get_disclosure_audit(
        self,
        session_id: str
    ) -> List[DisclosureRecord]:
        """Get all disclosures for session (for audit log)."""
```

### Compliance Models (compliance.py)

```python
class OfferingPriceComponents(BaseModel):
    """SB 766 compliant price breakdown."""
    base_vehicle_price: float
    doc_fee: float
    mandatory_addons: List[AddOn]  # Pre-installed, non-optional
    total_offering_price: float  # Sum of above
    # NOT included: taxes, registration (government charges)

class ComplianceCheckResult(BaseModel):
    allowed: bool
    violation: Optional[ComplianceViolation] = None
    required_action: Optional[str] = None  # e.g., "SHOW_OFFERING_PRICE"

class ComplianceViolation(BaseModel):
    code: str  # e.g., "SB766_OFFERING_PRICE_REQUIRED"
    regulation: str  # "California SB 766"
    message: str
    blocked_action: str  # What was prevented
    required_disclosure: Optional[str] = None

class AddOnValidationResult(BaseModel):
    valid: bool
    addon_id: str
    reason: Optional[str] = None  # Why blocked
    regulation: Optional[str] = None  # e.g., "CARS Act Valueless Add-on"
```

---

## Chat Router Integration

### Modified Payment Flow in chat.py

```python
async def _handle_payment_estimate(session_id: str, vehicle_id: int, ...):
    # NEW: Compliance check before calculation
    compliance = ComplianceSentinel()
    check = await compliance.check_payment_allowed(session_id, vehicle_id)

    if not check.allowed:
        # Must show offering price first
        vehicle = await get_vehicle(vehicle_id)
        offering = await build_offering_price(vehicle)

        # Record disclosure
        tracker = DisclosureTracker()
        tracker.record_offering_price_shown(session_id, vehicle_id, offering.total, offering)

        # Return offering price response (not payment)
        return ChatResponse(
            response=format_offering_price_disclosure(offering),
            metadata=ChatMetadata(intent="OFFERING_PRICE_DISCLOSURE", ...)
        )

    # Proceed with payment calculation...
```

---

## Session Context Extensions

Add to `session_context.py`:

```python
@dataclass
class SessionContext:
    # ... existing fields ...
    disclosures_shown: Dict[int, DisclosureRecord] = field(default_factory=dict)
    # Key: vehicle_id, Value: disclosure record with timestamp
```

---

## Acceptance Tests

### Test File: `backend/tests/test_compliance_sentinel.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T02-01 | `test_payment_blocked_without_offering_price` | Payment request without prior disclosure returns `allowed=False` |
| T02-02 | `test_payment_allowed_after_offering_price` | Payment request after disclosure returns `allowed=True` |
| T02-03 | `test_offering_price_includes_doc_fee` | Offering price = base + doc_fee + mandatory_addons |
| T02-04 | `test_offering_price_excludes_taxes` | Offering price does NOT include sales tax |
| T02-05 | `test_addon_blocked_no_benefit_statement` | AddOn with `benefit_statement=None` returns `valid=False` |
| T02-06 | `test_addon_blocked_ev_oil_change` | Oil change addon on electric vehicle returns `valid=False` |
| T02-07 | `test_addon_allowed_valid_benefit` | AddOn with valid benefit statement returns `valid=True` |
| T02-08 | `test_compliance_violation_logged` | Violation creates audit log entry with payload_hash |

### Test File: `backend/tests/test_sb766_disclosure.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T02-09 | `test_chat_payment_triggers_disclosure` | "What's the monthly payment?" returns offering price first |
| T02-10 | `test_chat_after_disclosure_returns_payment` | Second payment request (after disclosure) returns payment |
| T02-11 | `test_disclosure_per_vehicle` | Disclosure for vehicle A does not satisfy vehicle B |
| T02-12 | `test_disclosure_persists_in_session` | Disclosure valid for entire session |
| T02-13 | `test_disclosure_format_sb766_compliant` | Response includes itemized breakdown per SB 766 format |

### Test File: `backend/tests/test_valueless_addons.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T02-14 | `test_nitrogen_on_nitrogen_filled_blocked` | Nitrogen addon on already-nitrogen-filled vehicle blocked |
| T02-15 | `test_oil_change_on_ev_blocked` | Oil change addon on EV blocked |
| T02-16 | `test_theft_etch_no_benefit_blocked` | Theft etch with null benefit_statement blocked |
| T02-17 | `test_valid_addon_allowed` | Valid addon with documented benefit allowed |
| T02-18 | `test_addon_validation_logged` | Validation result logged to audit_logs |

---

## Demo Script Alignment

From `02_strategic_blueprint.md` §5 Scene 1:

**User:** "How much is the monthly payment on the 2024 Camry?"

**Expected System Behavior:**
1. `Conversationalist` detects `Intent: Payment_Inquiry`
2. `Compliance_Sentinel` intercepts: **Constraint Violation** - "Cannot quote payment without Offering Price disclosure"
3. System retrieves `Base_Price`, `Doc_Fee`, `Mandatory_Addons`
4. System calculates `Total_Offering_Price`
5. Response: *"Before we get to payments, the Offering Price for this Camry is $24,500, which includes the vehicle and the $85 doc fee. Government taxes are extra. Now, would you like to see financing options?"*

---

## Audit Log Requirements

Every compliance check must log:

```json
{
  "transaction_id": "uuid-v4",
  "timestamp": "2026-01-23T...",
  "actor": "agent:compliance",
  "event_type": "disclosure_presented",
  "payload_hash": "sha256-of-offering-price-json",
  "regulatory_flags": {
    "sb766_disclosure_verified": true
  }
}
```

---

## Definition of Done

- [ ] `ComplianceSentinel` service created with all methods
- [ ] `DisclosureTracker` service created
- [ ] Compliance Pydantic models created
- [ ] Chat router intercepts payment inquiries with compliance check
- [ ] Session context tracks disclosures per vehicle
- [ ] All 18 acceptance tests pass
- [ ] Demo script Scene 1 flow works as specified
- [ ] Audit logs include compliance events with payload hashes
- [ ] No regressions in existing tests
