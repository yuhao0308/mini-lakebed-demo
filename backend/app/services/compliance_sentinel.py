"""
T02: Compliance Sentinel Service

The "Guard" agent - enforces regulatory compliance in real-time.
Per tasks/T02_core_compliance.md

Responsibilities:
- Block payment quotes without prior Offering Price disclosure (SB 766)
- Validate add-ons have documented benefit for specific vehicle
- Log all compliance events with payload hashes
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from app.models.compliance import (
    ComplianceCheckResult,
    ComplianceViolation,
    AddOnValidationResult,
    ComplianceEvent,
)
from app.models.schemas import AddOn, OfferingPriceComponents
from app.services.disclosure_tracker import check_offering_price_disclosed
from app.services.database import execute_insert, execute_one


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
        disclosed = await check_offering_price_disclosed(session_id, vehicle_id)

        if disclosed:
            return ComplianceCheckResult(
                allowed=True,
                violation=None,
                required_action=None
            )

        # Offering price not disclosed - block payment quote
        violation = ComplianceViolation(
            code="SB766_OFFERING_PRICE_REQUIRED",
            regulation="California SB 766",
            message="Cannot quote payment without Offering Price disclosure. "
                    "The total cash price must be disclosed before discussing financing.",
            blocked_action="PAYMENT_QUOTE",
            required_disclosure="OFFERING_PRICE"
        )

        # Log the violation
        await self._log_compliance_event(
            event_type="payment_blocked_no_disclosure",
            session_id=session_id,
            vehicle_id=vehicle_id,
            details={
                "violation_code": violation.code,
                "regulation": violation.regulation
            },
            regulatory_flags={"sb766_disclosure_verified": False}
        )

        return ComplianceCheckResult(
            allowed=False,
            violation=violation,
            required_action="SHOW_OFFERING_PRICE"
        )

    async def validate_addon(
        self,
        vehicle: Dict[str, Any],
        addon: AddOn
    ) -> AddOnValidationResult:
        """
        Check if add-on provides documented benefit for this specific vehicle.

        Rules:
        - If fuel_type='electric' and addon.name contains 'oil change' -> BLOCK
        - If addon.benefit_statement is None/empty -> BLOCK
        - If addon.compliance_check_passed is False -> BLOCK
        """
        fuel_type = vehicle.get("fuel_type", "").lower()
        addon_name_lower = addon.name.lower()

        # Rule 1: No oil changes on electric vehicles
        if fuel_type == "electric" and "oil" in addon_name_lower:
            await self._log_addon_validation(
                addon=addon,
                vehicle_id=vehicle.get("id"),
                valid=False,
                reason="Oil change service not applicable to electric vehicle"
            )
            return AddOnValidationResult(
                valid=False,
                addon_id=addon.add_on_id,
                addon_name=addon.name,
                reason="Oil change service not applicable to electric vehicle",
                regulation="CARS Act - Valueless Add-on"
            )

        # Rule 2: No nitrogen fill on vehicles already with nitrogen
        # Check if vehicle already has nitrogen-filled tires (from add_ons)
        existing_addons = vehicle.get("add_ons")
        if existing_addons:
            try:
                existing = json.loads(existing_addons) if isinstance(existing_addons, str) else existing_addons
                for existing_addon in existing:
                    if "nitrogen" in existing_addon.get("name", "").lower():
                        if "nitrogen" in addon_name_lower:
                            await self._log_addon_validation(
                                addon=addon,
                                vehicle_id=vehicle.get("id"),
                                valid=False,
                                reason="Vehicle already has nitrogen-filled tires"
                            )
                            return AddOnValidationResult(
                                valid=False,
                                addon_id=addon.add_on_id,
                                addon_name=addon.name,
                                reason="Vehicle already has nitrogen-filled tires",
                                regulation="CARS Act - Valueless Add-on"
                            )
            except (json.JSONDecodeError, TypeError):
                pass

        # Rule 3: No benefit statement
        if not addon.benefit_statement or addon.benefit_statement.strip() == "":
            await self._log_addon_validation(
                addon=addon,
                vehicle_id=vehicle.get("id"),
                valid=False,
                reason="Add-on has no documented benefit statement"
            )
            return AddOnValidationResult(
                valid=False,
                addon_id=addon.add_on_id,
                addon_name=addon.name,
                reason="Add-on has no documented benefit statement",
                regulation="CARS Act - Valueless Add-on"
            )

        # Rule 4: Compliance check not passed
        if not addon.compliance_check_passed:
            await self._log_addon_validation(
                addon=addon,
                vehicle_id=vehicle.get("id"),
                valid=False,
                reason="Add-on has not passed compliance check"
            )
            return AddOnValidationResult(
                valid=False,
                addon_id=addon.add_on_id,
                addon_name=addon.name,
                reason="Add-on has not passed compliance check",
                regulation="CARS Act - Valueless Add-on"
            )

        # All checks passed
        await self._log_addon_validation(
            addon=addon,
            vehicle_id=vehicle.get("id"),
            valid=True,
            reason=None
        )
        return AddOnValidationResult(
            valid=True,
            addon_id=addon.add_on_id,
            addon_name=addon.name,
            reason=None,
            regulation=None
        )

    async def enforce_offering_price_first(
        self,
        intent: str,
        session_id: str,
        vehicle_id: int
    ) -> Optional[ComplianceViolation]:
        """
        Core SB 766 enforcement logic.

        If intent is PAYMENT_INQUIRY/PAYMENT_ESTIMATE and offering price not yet disclosed:
        Return ComplianceViolation forcing disclosure first.
        """
        payment_intents = ["payment_inquiry", "payment_estimate"]

        if intent.lower() not in payment_intents:
            return None

        disclosed = await check_offering_price_disclosed(session_id, vehicle_id)

        if disclosed:
            return None

        # Must show offering price first
        return ComplianceViolation(
            code="SB766_OFFERING_PRICE_REQUIRED",
            regulation="California SB 766",
            message="Before we get to payments, we must first disclose the Offering Price.",
            blocked_action="PAYMENT_INQUIRY",
            required_disclosure="OFFERING_PRICE"
        )

    async def _log_compliance_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        vehicle_id: Optional[int] = None,
        details: Optional[dict] = None,
        regulatory_flags: Optional[dict] = None
    ) -> str:
        """Log a compliance event to the audit_logs table."""
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Create payload for hashing
        payload = {
            "transaction_id": transaction_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "session_id": session_id,
            "vehicle_id": vehicle_id,
            "details": details or {},
            "regulatory_flags": regulatory_flags or {}
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        try:
            await execute_insert(
                """
                INSERT INTO audit_logs (
                    session_id, action, transaction_id, actor, event_type,
                    payload_hash, regulatory_flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id or "",
                    f"compliance:{event_type}",
                    transaction_id,
                    "agent:compliance",
                    event_type,
                    payload_hash,
                    json.dumps(regulatory_flags or {})
                )
            )
        except Exception as e:
            # Log error but don't fail the compliance check
            print(f"Warning: Failed to log compliance event: {e}")

        return transaction_id

    async def _log_addon_validation(
        self,
        addon: AddOn,
        vehicle_id: Optional[int],
        valid: bool,
        reason: Optional[str]
    ) -> None:
        """Log add-on validation result."""
        await self._log_compliance_event(
            event_type="addon_validation",
            vehicle_id=vehicle_id,
            details={
                "addon_id": addon.add_on_id,
                "addon_name": addon.name,
                "valid": valid,
                "reason": reason
            },
            regulatory_flags={
                "cars_act_validated": True,
                "addon_approved": valid
            }
        )


async def build_offering_price(vehicle: Dict[str, Any]) -> OfferingPriceComponents:
    """
    Build SB 766 compliant offering price components from a vehicle.

    Per spec: Offering Price = base + doc_fee + mandatory_addons
    Does NOT include taxes/registration (government charges).
    """
    base_price = vehicle.get("price", 0)
    sb766_price = vehicle.get("sb766_offering_price", base_price)

    # Parse add-ons if present
    mandatory_addons = []
    addons_total = 0
    add_ons_raw = vehicle.get("add_ons")
    if add_ons_raw:
        try:
            addons_list = json.loads(add_ons_raw) if isinstance(add_ons_raw, str) else add_ons_raw
            for addon_data in addons_list:
                addon = AddOn(
                    add_on_id=addon_data.get("add_on_id", "unknown"),
                    name=addon_data.get("name", "Unknown"),
                    price=addon_data.get("price", 0),
                    benefit_statement=addon_data.get("benefit_statement"),
                    compliance_check_passed=addon_data.get("compliance_check_passed", False)
                )
                mandatory_addons.append(addon)
                addons_total += addon.price
        except (json.JSONDecodeError, TypeError):
            pass

    # Calculate doc fee (sb766_price - base_price - addons)
    # or use a default doc fee
    doc_fee = 85.0  # Default doc fee

    # If sb766_offering_price is set, use it as total
    if sb766_price and sb766_price != base_price:
        total = sb766_price
    else:
        total = base_price + doc_fee + addons_total

    return OfferingPriceComponents(
        base_vehicle_price=base_price,
        doc_fee=doc_fee,
        mandatory_addons=mandatory_addons,
        total_offering_price=total
    )


def format_offering_price_disclosure(
    vehicle: Dict[str, Any],
    components: OfferingPriceComponents
) -> str:
    """
    Format the offering price disclosure message per SB 766.

    Per spec Demo Script Scene 1:
    "Before we get to payments, the Offering Price for this Camry is $24,500,
    which includes the vehicle and the $85 doc fee. Government taxes are extra.
    Now, would you like to see financing options?"
    """
    vehicle_name = f"{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}"

    # Build add-on text if any
    addon_text = ""
    if components.mandatory_addons:
        addon_names = [a.name for a in components.mandatory_addons]
        addon_text = f", {', '.join(addon_names)}"

    response = (
        f"Before we get to payments, the **Offering Price** for this "
        f"**{vehicle_name}** is **${components.total_offering_price:,.0f}**.\n\n"
        f"This includes:\n"
        f"- Base vehicle price: ${components.base_vehicle_price:,.0f}\n"
        f"- Documentation fee: ${components.doc_fee:,.0f}"
    )

    if components.mandatory_addons:
        response += f"\n- Pre-installed add-ons: "
        addon_details = [f"{a.name} (${a.price:,.0f})" for a in components.mandatory_addons]
        response += ", ".join(addon_details)

    response += (
        f"\n\n*Government taxes and registration fees are extra.*\n\n"
        f"Would you like to see financing options for this vehicle?"
    )

    return response
