# Models package
from app.models.schemas import (
    Vehicle,
    VehicleSearchParams,
    VehicleSearchResponse,
    LenderRule,
    PaymentRequest,
    PaymentResponse,
    PaymentErrorResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    CreditTier,
    BodyStyle,
    VehicleStatus,
    FuelType,
    DaysBasis,
    # T01: Data Foundation Models
    AddOn,
    OfferingPriceComponents,
    TradeIn,
    TaxCalculation,
    TaxRate,
    AdverseActionCode,
    LenderRuleExtended,
)

# T01: Customer Profile Models
from app.models.customer import (
    CustomerProfile,
    CustomerCreate,
    CustomerIdentity,
    CustomerResidence,
    CustomerEmployment,
    FCRAConsentEntry,
    PIIClearanceLevel,
    ResidenceType,
    ConsentType,
)

# T01: Deal Jacket Models
from app.models.deal import (
    DealJacket,
    DealCreate,
    DealStatus,
    DealType,
    DealFees,
    LendingTerms,
    AuditTrailEntry,
)

# T01: Compliance Log Models
from app.models.compliance_log import (
    ComplianceLog,
    ComplianceLogCreate,
    AuditLogEntry,
    EventType,
    Actor,
    AdverseActionReason,
    CreditDataUsed,
    NoticeDetails,
    RegulatoryFlags,
    ContextSnapshot,
)

__all__ = [
    # Original exports
    "Vehicle",
    "VehicleSearchParams",
    "VehicleSearchResponse",
    "LenderRule",
    "PaymentRequest",
    "PaymentResponse",
    "PaymentErrorResponse",
    "ChatRequest",
    "ChatResponse",
    "HealthResponse",
    "CreditTier",
    "BodyStyle",
    "VehicleStatus",
    "FuelType",
    "DaysBasis",
    # T01: Schema Models
    "AddOn",
    "OfferingPriceComponents",
    "TradeIn",
    "TaxCalculation",
    "TaxRate",
    "AdverseActionCode",
    "LenderRuleExtended",
    # T01: Customer Models
    "CustomerProfile",
    "CustomerCreate",
    "CustomerIdentity",
    "CustomerResidence",
    "CustomerEmployment",
    "FCRAConsentEntry",
    "PIIClearanceLevel",
    "ResidenceType",
    "ConsentType",
    # T01: Deal Models
    "DealJacket",
    "DealCreate",
    "DealStatus",
    "DealType",
    "DealFees",
    "LendingTerms",
    "AuditTrailEntry",
    # T01: Compliance Models
    "ComplianceLog",
    "ComplianceLogCreate",
    "AuditLogEntry",
    "EventType",
    "Actor",
    "AdverseActionReason",
    "CreditDataUsed",
    "NoticeDetails",
    "RegulatoryFlags",
    "ContextSnapshot",
]
