"""
T05: Authorization Service

OpenFGA authorization wrapper for fine-grained access control.
Per tasks/T05_governance.md and 03_implementation_dummy_data_plan.md §5

Provides check() method for policy enforcement points.
Falls back to simple RBAC if OpenFGA is unavailable.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Set, List
from dataclasses import dataclass, field

from app.models.authorization import (
    AuthRelation,
    AuthCheckResult,
    ObjectType,
    ClearanceLevel
)

logger = logging.getLogger(__name__)

# Load tuples from JSON file for local fallback
TUPLES_FILE = Path(__file__).parent.parent.parent.parent / "openfga" / "tuples.json"


@dataclass
class AuthorizationTuple:
    """Represents an authorization relationship."""
    user: str
    relation: str
    object: str


@dataclass
class LocalAuthStore:
    """
    Local authorization store for when OpenFGA is not available.

    Simulates OpenFGA behavior using in-memory tuples.
    """
    tuples: List[AuthorizationTuple] = field(default_factory=list)

    # Index for fast lookups: object -> list of (user, relation)
    _object_index: Dict[str, List[tuple]] = field(default_factory=dict)

    def add_tuple(self, user: str, relation: str, obj: str):
        """Add a tuple to the store."""
        t = AuthorizationTuple(user=user, relation=relation, object=obj)
        self.tuples.append(t)

        # Update index
        if obj not in self._object_index:
            self._object_index[obj] = []
        self._object_index[obj].append((user, relation))

    def has_tuple(self, user: str, relation: str, obj_type: str, obj_id: str) -> bool:
        """Check if a tuple exists with exact match."""
        obj = f"{obj_type}:{obj_id}"
        return self._has_direct_relation(user, relation, obj)

    def _load_initial_tuples(self):
        """Load initial tuples from JSON file."""
        if TUPLES_FILE.exists():
            try:
                with open(TUPLES_FILE) as f:
                    data = json.load(f)
                    for t in data.get("tuples", []):
                        self.add_tuple(
                            user=t["user"],
                            relation=t["relation"],
                            obj=t["object"]
                        )
                logger.info(f"LocalAuthStore loaded {len(data.get('tuples', []))} tuples")
            except Exception as e:
                logger.warning(f"LocalAuthStore could not load tuples file: {e}")

    def check(self, user: str, relation: str, obj: str) -> bool:
        """
        Check if user has relation to object.

        Implements transitive relation resolution per OpenFGA model.
        """
        # Direct check
        if self._has_direct_relation(user, relation, obj):
            return True

        # Check derived relations based on model rules
        return self._check_derived_relations(user, relation, obj)

    def _has_direct_relation(self, user: str, relation: str, obj: str) -> bool:
        """Check for direct tuple match."""
        if obj in self._object_index:
            for stored_user, stored_relation in self._object_index[obj]:
                if stored_user == user and stored_relation == relation:
                    return True
        return False

    def _check_derived_relations(self, user: str, relation: str, obj: str) -> bool:
        """
        Check derived relations per OpenFGA model.

        For example:
        - editor includes owner
        - viewer includes editor
        - auditor includes general_manager
        """
        obj_type = obj.split(":")[0] if ":" in obj else ""

        if obj_type == "deal":
            return self._check_deal_relations(user, relation, obj)
        elif obj_type == "compliance_log":
            return self._check_compliance_log_relations(user, relation, obj)
        elif obj_type == "customer_profile":
            return self._check_customer_profile_relations(user, relation, obj)

        return False

    def _check_deal_relations(self, user: str, relation: str, obj: str) -> bool:
        """Check deal-specific derived relations."""
        # Get the dealership for this deal
        dealership = self._get_deal_dealership(obj)

        if relation == "viewer":
            # viewer: [user, dealership#member] or editor
            if self._has_direct_relation(user, "viewer", obj):
                return True
            if self.check(user, "editor", obj):
                return True
            # Check if user is member of deal's dealership
            if dealership and self._has_direct_relation(user, "member", dealership):
                return True

        elif relation == "editor":
            # editor: [user] or owner or dealership#finance_manager or dealership#sales_manager
            if self._has_direct_relation(user, "editor", obj):
                return True
            if self._has_direct_relation(user, "owner", obj):
                return True
            if dealership:
                if self._has_direct_relation(user, "finance_manager", dealership):
                    return True
                if self._has_direct_relation(user, "sales_manager", dealership):
                    return True

        elif relation == "auditor":
            # auditor: [user] or dealership#general_manager
            if self._has_direct_relation(user, "auditor", obj):
                return True
            if dealership and self._has_direct_relation(user, "general_manager", dealership):
                return True

        return False

    def _check_compliance_log_relations(self, user: str, relation: str, obj: str) -> bool:
        """Check compliance_log-specific derived relations."""
        if relation == "viewer":
            # viewer: [user] or deal#auditor
            if self._has_direct_relation(user, "viewer", obj):
                return True
            # Would need to check deal#auditor but we don't have deal link here

        elif relation == "sensitive_viewer":
            # sensitive_viewer: [user] - only direct assignment
            return self._has_direct_relation(user, "sensitive_viewer", obj)

        return False

    def _check_customer_profile_relations(self, user: str, relation: str, obj: str) -> bool:
        """Check customer_profile-specific derived relations."""
        if relation == "can_view_pii":
            # can_view_pii: [user] or owner
            if self._has_direct_relation(user, "can_view_pii", obj):
                return True
            if self._has_direct_relation(user, "owner", obj):
                return True

        elif relation == "can_view_masked":
            # can_view_masked: [user, dealership#member]
            if self._has_direct_relation(user, "can_view_masked", obj):
                return True
            # Check dealership membership - need to know which dealership
            # For simplicity, check all dealerships the user is a member of
            for t in self.tuples:
                if t.user == user and t.relation == "member" and t.object.startswith("dealership:"):
                    return True

        return False

    def _get_deal_dealership(self, deal_obj: str) -> Optional[str]:
        """Get the dealership associated with a deal."""
        if deal_obj in self._object_index:
            for stored_user, stored_relation in self._object_index[deal_obj]:
                if stored_relation == "dealership" and stored_user.startswith("dealership:"):
                    return stored_user
        return None


class AuthorizationService:
    """
    OpenFGA authorization wrapper.

    Provides check() method for policy enforcement points.
    Falls back to simple RBAC if OpenFGA unavailable.

    Per spec §3.3: Fine-grained authorization integrated into RAG pipeline.
    """

    def __init__(self, openfga_url: Optional[str] = None):
        """
        Initialize authorization service.

        Args:
            openfga_url: OpenFGA server URL. If None, uses local fallback.
        """
        self.openfga_url = openfga_url or os.getenv("OPENFGA_API_URL")
        self.openfga_store_id = os.getenv("OPENFGA_STORE_ID")
        self.openfga_model_id = os.getenv("OPENFGA_MODEL_ID")
        self.local_store = LocalAuthStore()
        self.mode = "local_rbac_fallback"
        self.openfga_configured = bool(
            self.openfga_url and self.openfga_store_id and self.openfga_model_id
        )
        self.mode_reason = (
            "OpenFGA client is not wired in this demo runtime; using local tuple-backed RBAC/ReBAC fallback."
        )
        self._load_initial_tuples()

        if self.openfga_configured:
            logger.warning(
                "OpenFGA environment variables detected, but the runtime still uses local fallback mode."
            )

    def _load_initial_tuples(self):
        """Load initial tuples from JSON file."""
        if TUPLES_FILE.exists():
            try:
                with open(TUPLES_FILE) as f:
                    data = json.load(f)
                    for t in data.get("tuples", []):
                        self.local_store.add_tuple(
                            user=t["user"],
                            relation=t["relation"],
                            obj=t["object"]
                        )
                logger.info(f"Loaded {len(data.get('tuples', []))} authorization tuples")
            except Exception as e:
                logger.warning(f"Could not load tuples file: {e}")

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

        Args:
            user_id: User identifier (with or without 'user:' prefix)
            relation: Relation to check
            object_type: Type of object (deal, compliance_log, etc.)
            object_id: Object identifier

        Returns:
            AuthCheckResult with allowed status and reason
        """
        # Normalize user_id format
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        # Construct object string
        obj = f"{object_type}:{object_id}"

        # Use local store for now (OpenFGA integration would go here)
        allowed = self.local_store.check(user_id, relation.value, obj)

        reason = None
        if not allowed:
            reason = f"User {user_id} does not have {relation.value} relation to {obj}"

        return AuthCheckResult(
            allowed=allowed,
            user=user_id,
            relation=relation.value,
            object_type=object_type,
            object_id=object_id,
            reason=reason
        )

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

        Args:
            user: User identifier
            relation: Relation name
            object_type: Type of object
            object_id: Object identifier

        Returns:
            True if tuple was written successfully
        """
        # Normalize user format
        if not user.startswith("user:") and not user.startswith("dealership:"):
            user = f"user:{user}"

        obj = f"{object_type}:{object_id}"

        try:
            self.local_store.add_tuple(user, relation, obj)
            logger.info(f"Wrote tuple: ({user}, {relation}, {obj})")
            return True
        except Exception as e:
            logger.error(f"Failed to write tuple: {e}")
            return False

    async def check_deal_edit_allowed(
        self,
        user_id: str,
        deal_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user edit this deal?

        Per spec §5.2.1: Only owner or finance_manager can mutate financial_structure.

        Args:
            user_id: User identifier
            deal_id: Deal identifier

        Returns:
            AuthCheckResult for editor relation
        """
        return await self.check(
            user_id=user_id,
            relation=AuthRelation.EDITOR,
            object_type="deal",
            object_id=deal_id
        )

    async def check_pii_access_allowed(
        self,
        user_id: str,
        customer_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user see full PII?

        Per spec §5.2.2: Generic members can view deal but not credit report.

        Args:
            user_id: User identifier
            customer_id: Customer profile identifier

        Returns:
            AuthCheckResult for can_view_pii relation
        """
        return await self.check(
            user_id=user_id,
            relation=AuthRelation.CAN_VIEW_PII,
            object_type="customer_profile",
            object_id=customer_id
        )

    async def check_deal_view_allowed(
        self,
        user_id: str,
        deal_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user view this deal?

        Args:
            user_id: User identifier
            deal_id: Deal identifier

        Returns:
            AuthCheckResult for viewer relation
        """
        return await self.check(
            user_id=user_id,
            relation=AuthRelation.VIEWER,
            object_type="deal",
            object_id=deal_id
        )

    async def check_audit_access_allowed(
        self,
        user_id: str,
        deal_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user audit this deal?

        Args:
            user_id: User identifier
            deal_id: Deal identifier

        Returns:
            AuthCheckResult for auditor relation
        """
        return await self.check(
            user_id=user_id,
            relation=AuthRelation.AUDITOR,
            object_type="deal",
            object_id=deal_id
        )

    async def check_sensitive_log_access(
        self,
        user_id: str,
        log_id: str
    ) -> AuthCheckResult:
        """
        Convenience method: Can user view sensitive compliance log details?

        Per spec: Only compliance officers can see raw credit denial reasons.

        Args:
            user_id: User identifier
            log_id: Compliance log identifier

        Returns:
            AuthCheckResult for sensitive_viewer relation
        """
        return await self.check(
            user_id=user_id,
            relation=AuthRelation.SENSITIVE_VIEWER,
            object_type="compliance_log",
            object_id=log_id
        )

    def get_status(self) -> Dict[str, object]:
        """Return authorization mode/configuration status for diagnostics."""
        return {
            "mode": self.mode,
            "mode_reason": self.mode_reason,
            "openfga_configured": self.openfga_configured,
            "openfga_api_url_set": bool(self.openfga_url),
            "openfga_store_id_set": bool(self.openfga_store_id),
            "openfga_model_id_set": bool(self.openfga_model_id),
            "local_tuple_count": len(self.local_store.tuples),
        }

    def get_user_clearance_level(
        self,
        user_id: str,
        customer_id: str
    ) -> ClearanceLevel:
        """
        Determine user's clearance level for a customer profile.

        High: Owner or explicitly granted can_view_pii
        Medium: Finance manager or compliance officer
        Low: Everyone else (dealership member)

        Args:
            user_id: User identifier
            customer_id: Customer profile identifier

        Returns:
            ClearanceLevel enum value
        """
        # Normalize user_id
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        obj = f"customer_profile:{customer_id}"

        # Check if owner or has can_view_pii
        if self.local_store.check(user_id, "can_view_pii", obj):
            return ClearanceLevel.HIGH
        if self.local_store.check(user_id, "owner", obj):
            return ClearanceLevel.HIGH

        # Check if finance manager (medium clearance)
        for t in self.local_store.tuples:
            if t.user == user_id and t.relation == "finance_manager":
                return ClearanceLevel.MEDIUM

        # Default to low clearance
        return ClearanceLevel.LOW


# Module-level singleton
_auth_service: Optional[AuthorizationService] = None


def get_authorization_service() -> AuthorizationService:
    """Get or create the authorization service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthorizationService()
    return _auth_service


# Alias for convenience
def get_auth_service() -> AuthorizationService:
    """Alias for get_authorization_service."""
    return get_authorization_service()
