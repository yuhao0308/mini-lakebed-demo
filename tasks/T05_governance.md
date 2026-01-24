# T05: Governance (OpenFGA / PII Protection)

**Priority:** Medium
**Status:** Not Started
**Depends On:** T01 (Data Foundation), T03 (Credit Flow)
**Blocked By:** T01

---

## Objective

Implement fine-grained authorization using OpenFGA and PII protection middleware. This ensures that users only access data they're authorized to see, and that sensitive data is never leaked to the LLM context.

---

## Spec References

| Spec File | Section | Requirement |
|-----------|---------|-------------|
| `02_strategic_blueprint.md` | §3.3 Security Architecture: RAG + OpenFGA | Fine-grained authorization integrated into RAG pipeline |
| `02_strategic_blueprint.md` | §3.3 Relationship-Based Access Control | User → Application → Document permission chains |
| `02_strategic_blueprint.md` | §4 User Story 6: NPI Data Redaction | SSN/Account numbers redacted before LLM context |
| `02_strategic_blueprint.md` | §4 User Story 10: Immutable Audit Log | Merkle tree of conversation history |
| `03_implementation_dummy_data_plan.md` | §5. Governance Controls: The OpenFGA Model | ReBAC model definition with DSL |
| `03_implementation_dummy_data_plan.md` | §5.1 The Authorization Model | User, Dealership, Deal, ComplianceLog types and relations |
| `03_implementation_dummy_data_plan.md` | §5.2 Policy Enforcement Points | Deal modification lock, PII access control |
| `03_implementation_dummy_data_plan.md` | §5.3 PII Scrubbing & Data Masking | SSN → `***-**-6789`, DOB → `YYYY-MM-01`, email masked |
| `03_implementation_dummy_data_plan.md` | §6.3 Governance Completeness | Cross-store isolation, audit trail fidelity |

---

## Files to Create

| File | Purpose |
|------|---------|
| `openfga/model.fga` | Authorization model DSL |
| `openfga/tuples.json` | Initial relationship tuples for testing |
| `backend/app/services/authorization.py` | OpenFGA check wrapper |
| `backend/app/middleware/pii_scrubber.py` | PII redaction before LLM |
| `backend/app/services/audit_hasher.py` | SHA-256 payload hashing for audit logs |
| `backend/app/models/authorization.py` | Pydantic models for auth checks |
| `backend/tests/test_authorization.py` | Authorization policy tests |
| `backend/tests/test_pii_scrubber.py` | PII redaction tests |
| `backend/tests/test_audit_integrity.py` | Hash chain verification tests |

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/main.py` | Add PII scrubber middleware |
| `backend/app/routers/chat.py` | Check authorization before data access |
| `backend/app/services/llm.py` | Pass scrubbed context to LLM |
| `backend/app/services/database.py` | Log payload hashes on writes |
| `docker-compose.yml` | Add OpenFGA service (optional for local dev) |

---

## Implementation Specifications

### OpenFGA Model (model.fga)

Per `03_implementation_dummy_data_plan.md` §5.1:

```dsl
model
  schema 1.1

type user

type dealership
  relations
    define member: [user]
    define general_manager: [user]
    define finance_manager: [user]
    define sales_manager: [user]

type deal
  relations
    define owner: [user]
    define dealership: [dealership]
    # A viewer can see the deal structure but not PII
    define viewer: [user, dealership#member] or editor
    # An editor can change numbers
    define editor: [user] or owner or dealership#finance_manager or dealership#sales_manager
    # An auditor can see the history but change nothing
    define auditor: [user] or dealership#general_manager

type compliance_log
  relations
    define viewer: [user] or deal#auditor
    # Only specific compliance officers can see the raw credit denial reasons
    define sensitive_viewer: [user]

type customer_profile
  relations
    define owner: [user]  # The customer themselves
    define can_view_pii: [user] or owner
    define can_view_masked: [user, dealership#member]
```

### authorization.py

```python
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class AuthRelation(str, Enum):
    """Authorization relations from OpenFGA model."""
    VIEWER = "viewer"
    EDITOR = "editor"
    AUDITOR = "auditor"
    SENSITIVE_VIEWER = "sensitive_viewer"
    CAN_VIEW_PII = "can_view_pii"
    CAN_VIEW_MASKED = "can_view_masked"


@dataclass
class AuthCheckResult:
    allowed: bool
    user: str
    relation: AuthRelation
    object_type: str
    object_id: str
    reason: Optional[str] = None


class AuthorizationService:
    """
    OpenFGA authorization wrapper.

    Provides check() method for policy enforcement points.
    Falls back to simple RBAC if OpenFGA unavailable.
    """

    async def check(
        self,
        user_id: str,
        relation: AuthRelation,
        object_type: str,
        object_id: str
    ) -> AuthCheckResult:
        """
        Check if user has relation to object.

        Examples:
        - check("user:sales_1", "editor", "deal", "deal_123")
        - check("user:finance_mgr", "sensitive_viewer", "compliance_log", "log_456")
        """

    async def write_tuple(
        self,
        user: str,
        relation: str,
        object_type: str,
        object_id: str
    ) -> bool:
        """
        Write authorization tuple.

        Called when deals are created to establish ownership.
        """

    async def check_deal_edit_allowed(
        self,
        user_id: str,
        deal_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user edit this deal?

        Per spec §5.2.1: Only owner or finance_manager can mutate financial_structure.
        """

    async def check_pii_access_allowed(
        self,
        user_id: str,
        customer_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user see full PII?

        Per spec §5.2.2: Generic members can view deal but not credit report.
        """
```

### pii_scrubber.py

```python
import re
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ScrubbingResult:
    """Result of PII scrubbing with audit trail."""
    original_hash: str  # Hash of original for audit
    scrubbed_data: Dict[str, Any]
    fields_scrubbed: list[str]


class PIIScrubber:
    """
    PII redaction middleware for LLM context.

    Per spec §5.3: Mask sensitive fields before passing to LLM.
    """

    # Regex patterns for PII detection
    SSN_PATTERN = re.compile(r'\d{3}-\d{2}-\d{4}')
    SSN_FULL_PATTERN = re.compile(r'\d{9}')
    ACCOUNT_PATTERN = re.compile(r'\b\d{10,16}\b')

    def scrub_ssn(self, ssn: str) -> str:
        """
        Mask SSN preserving last 4 digits.

        "123-45-6789" → "***-**-6789"
        """
        if not ssn:
            return ssn
        return f"***-**-{ssn[-4:]}"

    def scrub_dob(self, dob: str) -> str:
        """
        Mask DOB preserving year/month for age calculation.

        "1985-04-12" → "1985-04-01"

        Per spec: Allows AI to check "Is applicant over 18?"
        without exposing exact birthday.
        """
        if not dob:
            return dob
        parts = dob.split("-")
        if len(parts) == 3:
            return f"{parts[0]}-{parts[1]}-01"
        return dob

    def scrub_email(self, email: str) -> str:
        """
        Mask email preserving domain.

        "john.doe@example.com" → "j****@example.com"
        """
        if not email or "@" not in email:
            return email
        local, domain = email.split("@", 1)
        if len(local) > 1:
            return f"{local[0]}****@{domain}"
        return f"****@{domain}"

    def scrub_customer_profile(
        self,
        profile: Dict[str, Any],
        clearance_level: str
    ) -> ScrubbingResult:
        """
        Scrub customer profile based on clearance level.

        High clearance: Full access (no scrubbing)
        Medium clearance: SSN masked, DOB masked
        Low clearance: All PII masked
        """

    def scrub_for_llm_context(
        self,
        data: Dict[str, Any]
    ) -> ScrubbingResult:
        """
        Scrub any data structure before passing to LLM.

        Recursively finds and masks PII patterns.
        Always masks: SSN, full account numbers
        Preserves: Names, general location (city/state)
        """
```

### audit_hasher.py

```python
import hashlib
import json
from typing import Any
from datetime import datetime


class AuditHasher:
    """
    Cryptographic audit trail for tamper evidence.

    Per spec: Creates SHA-256 hash of payloads for immutability verification.
    """

    def hash_payload(self, payload: Any) -> str:
        """
        Generate SHA-256 hash of payload.

        Serializes to canonical JSON (sorted keys, no whitespace)
        for consistent hashing.
        """
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def create_audit_entry(
        self,
        actor: str,
        event_type: str,
        payload: Any,
        regulatory_flags: dict
    ) -> dict:
        """
        Create complete audit log entry with hash.

        Returns dict ready for database insertion.
        """
        return {
            "transaction_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "actor": actor,
            "event_type": event_type,
            "payload_hash": self.hash_payload(payload),
            "regulatory_flags": json.dumps(regulatory_flags)
        }

    def verify_chain(
        self,
        entries: list[dict]
    ) -> bool:
        """
        Verify audit log chain integrity.

        Each entry's hash should be verifiable against stored hash.
        """
```

---

## Middleware Integration

### PII Scrubber Middleware

```python
# In main.py
from fastapi import Request
from app.middleware.pii_scrubber import PIIScrubber

scrubber = PIIScrubber()

@app.middleware("http")
async def pii_scrubbing_middleware(request: Request, call_next):
    # Store scrubber in request state for use in LLM calls
    request.state.pii_scrubber = scrubber
    response = await call_next(request)
    return response
```

### Authorization Checks in Routes

```python
# In chat.py or payments.py
from app.services.authorization import AuthorizationService, AuthRelation

auth = AuthorizationService()

async def get_deal_details(deal_id: str, current_user: str):
    # Check authorization
    check = await auth.check(
        user_id=current_user,
        relation=AuthRelation.VIEWER,
        object_type="deal",
        object_id=deal_id
    )

    if not check.allowed:
        raise HTTPException(403, "Not authorized to view this deal")

    # Proceed with data retrieval...
```

---

## Acceptance Tests

### Test File: `backend/tests/test_authorization.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T05-01 | `test_owner_can_edit_deal` | Deal owner has `editor` relation |
| T05-02 | `test_finance_manager_can_edit_deal` | Finance manager has `editor` relation |
| T05-03 | `test_sales_rep_cannot_edit_other_deal` | Sales rep A cannot edit sales rep B's deal |
| T05-04 | `test_cross_store_isolation` | Store A member cannot view Store B deals |
| T05-05 | `test_general_manager_is_auditor` | GM has `auditor` but not `editor` |
| T05-06 | `test_member_viewer_not_sensitive` | Dealership member is `viewer` but not `sensitive_viewer` |
| T05-07 | `test_compliance_officer_sensitive` | Compliance officer has `sensitive_viewer` |
| T05-08 | `test_customer_owns_profile` | Customer has `can_view_pii` on own profile |
| T05-09 | `test_tuple_write_on_deal_create` | Deal creation writes ownership tuple |

### Test File: `backend/tests/test_pii_scrubber.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T05-10 | `test_ssn_scrubbed` | "123-45-6789" → "***-**-6789" |
| T05-11 | `test_dob_scrubbed` | "1985-04-12" → "1985-04-01" |
| T05-12 | `test_email_scrubbed` | "john@example.com" → "j****@example.com" |
| T05-13 | `test_account_number_scrubbed` | 16-digit number masked |
| T05-14 | `test_high_clearance_no_scrub` | High clearance returns original |
| T05-15 | `test_low_clearance_full_scrub` | Low clearance masks all PII |
| T05-16 | `test_llm_context_scrubbed` | Data passed to LLM has no raw SSN |
| T05-17 | `test_nested_pii_found` | Recursively finds PII in nested structures |

### Test File: `backend/tests/test_audit_integrity.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T05-18 | `test_payload_hash_sha256` | Hash is 64-char hex string |
| T05-19 | `test_hash_deterministic` | Same payload → same hash |
| T05-20 | `test_hash_changes_on_modification` | Modified payload → different hash |
| T05-21 | `test_audit_entry_complete` | Entry has all required fields |
| T05-22 | `test_chain_verification` | Unmodified chain passes verification |
| T05-23 | `test_tampered_chain_detected` | Modified entry fails verification |

---

## Completeness Checklist Tests

Per `03_implementation_dummy_data_plan.md` §6.3:

| Test ID | Spec Requirement | Test |
|---------|------------------|------|
| T05-24 | Cross-Store Isolation | Sales rep from Store A cannot view deal from Store B (expect FALSE) |
| T05-25 | Manager Override | Finance Manager can edit deal owned by Sales Rep (expect TRUE) |
| T05-26 | Audit Trail Fidelity | Every `selling_price` change logged with `user_id` and `timestamp` |
| T05-27 | Agent PII Restriction | AI Agent with "Low Clearance" cannot access `ssn_token` (expect NULL) |

---

## Definition of Done

- [ ] `openfga/model.fga` created with complete authorization model
- [ ] `AuthorizationService` implemented with check/write methods
- [ ] `PIIScrubber` middleware integrated into request pipeline
- [ ] `AuditHasher` generates SHA-256 hashes for all audit entries
- [ ] LLM context always passes through PII scrubber
- [ ] All 27 acceptance tests pass
- [ ] Cross-store isolation verified
- [ ] Audit log entries include `payload_hash` field
- [ ] No regressions in existing tests
