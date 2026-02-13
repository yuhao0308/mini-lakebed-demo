"""
T05: Authorization Models

Pydantic models for OpenFGA-based authorization.
Per tasks/T05_governance.md and 03_implementation_dummy_data_plan.md §5
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AuthRelation(str, Enum):
    """Authorization relations from OpenFGA model."""
    VIEWER = "viewer"
    EDITOR = "editor"
    AUDITOR = "auditor"
    SENSITIVE_VIEWER = "sensitive_viewer"
    CAN_VIEW_PII = "can_view_pii"
    CAN_VIEW_MASKED = "can_view_masked"
    OWNER = "owner"
    MEMBER = "member"
    FINANCE_MANAGER = "finance_manager"
    SALES_MANAGER = "sales_manager"
    GENERAL_MANAGER = "general_manager"


class ObjectType(str, Enum):
    """Object types in the authorization model."""
    USER = "user"
    DEALERSHIP = "dealership"
    DEAL = "deal"
    COMPLIANCE_LOG = "compliance_log"
    CUSTOMER_PROFILE = "customer_profile"


class ClearanceLevel(str, Enum):
    """PII clearance levels for data access."""
    HIGH = "high"       # Full access - no scrubbing
    MEDIUM = "medium"   # SSN masked, DOB masked
    LOW = "low"         # All PII masked


class AuthCheckRequest(BaseModel):
    """Request to check authorization."""
    user_id: str = Field(..., description="User identifier (e.g., 'user:sales_rep_1')")
    relation: AuthRelation = Field(..., description="Relation to check")
    object_type: ObjectType = Field(..., description="Type of object")
    object_id: str = Field(..., description="Object identifier")


class AuthCheckResult(BaseModel):
    """Result of an authorization check."""
    allowed: bool = Field(..., description="Whether access is allowed")
    user: str = Field(..., description="User who made the request")
    relation: str = Field(..., description="Relation that was checked")
    object_type: str = Field(..., description="Type of object")
    object_id: str = Field(..., description="Object identifier")
    reason: Optional[str] = Field(None, description="Reason for the decision")


class AuthTuple(BaseModel):
    """An authorization tuple (relationship)."""
    user: str = Field(..., description="User or userset (e.g., 'user:sales_1' or 'dealership:store_a#member')")
    relation: str = Field(..., description="Relation name")
    object: str = Field(..., description="Object (e.g., 'deal:deal_123')")


class AuthTupleWrite(BaseModel):
    """Request to write an authorization tuple."""
    tuples: List[AuthTuple] = Field(..., description="Tuples to write")


class UserContext(BaseModel):
    """User context for authorization decisions."""
    user_id: str = Field(..., description="User identifier")
    dealership_id: Optional[str] = Field(None, description="User's dealership")
    roles: List[str] = Field(default_factory=list, description="User's roles")
    clearance_level: ClearanceLevel = Field(
        default=ClearanceLevel.LOW,
        description="PII clearance level"
    )


class PolicyEnforcementPoint(BaseModel):
    """Describes a policy enforcement point in the system."""
    name: str = Field(..., description="Name of the enforcement point")
    resource_type: ObjectType = Field(..., description="Type of resource protected")
    required_relation: AuthRelation = Field(..., description="Required relation for access")
    description: str = Field(..., description="Description of what this protects")
