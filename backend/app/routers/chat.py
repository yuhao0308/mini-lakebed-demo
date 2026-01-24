"""
Chat router for conversational interface.

The LLM handles:
- Intent parsing
- Slot filling (extracting entities)
- Tool routing
- Generating natural language responses

The LLM must NOT:
- Invent inventory
- Generate payment amounts (deterministic calculator does this)
- Make approval decisions
"""

from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse, ToolCall, ChatMetadata
from app.services.llm import classify_intent, Intent, LLMResult, ExtractedEntities
from app.services.database import execute_query, execute_one
import uuid
import time

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main conversational endpoint.
    
    Processes natural language queries and routes to appropriate tools.
    """
    from app.services.session_context import add_chat_message, get_awaiting_input, clear_awaiting_input
    
    start_time = time.time()
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Save user message to chat history
    await add_chat_message(session_id, "user", request.message)
    
    # Check if we're awaiting a clarification response
    awaiting = await get_awaiting_input(session_id)
    
    if awaiting == "clarification":
        # Map user's response (A/B/C) to the appropriate intent
        mapped_intent = _map_clarification_response(request.message)
        if mapped_intent:
            await clear_awaiting_input(session_id)
            llm_result = LLMResult(
                intent=mapped_intent,
                entities=ExtractedEntities(),
                raw_response="clarification_mapped",
                confidence=0.9
            )
        else:
            # Couldn't map, proceed with normal classification
            llm_result = await classify_intent(request.message)
    elif awaiting == "confirm_payment_estimate":
        # Check for affirmative response
        msg = request.message.lower()
        if any(w in msg for w in ["yes", "sure", "please", "ok", "yeah", "yup", "correct", "do it"]):
            await clear_awaiting_input(session_id)
            
            # Route directly to payment estimate
            # Passing empty entities will trigger the "use context vehicle" logic
            response_text, tool_calls = await _handle_payment_estimate(ExtractedEntities(), [], session_id)
            
            # Save assistant response to chat history
            await add_chat_message(session_id, "assistant", response_text)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                session_id=session_id,
                response=response_text,
                tool_calls=tool_calls,
                metadata=ChatMetadata(
                    intent="payment_estimate_confirmed",
                    processing_time_ms=processing_time
                )
            )
        elif any(w in msg for w in ["no", "nah", "pass", "skip"]):
             await clear_awaiting_input(session_id)
             llm_result = await classify_intent(request.message)
        else:
             # Ambiguous response - clear state and classify normally
             await clear_awaiting_input(session_id)
             llm_result = await classify_intent(request.message)
    else:
        # Normal classification
        llm_result = await classify_intent(request.message)
    
    # Route to appropriate handler based on intent (with session context)
    response_text, tool_calls = await _route_intent(llm_result, request.message, session_id)
    
    # Save assistant response to chat history
    await add_chat_message(session_id, "assistant", response_text)
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        tool_calls=tool_calls,
        metadata=ChatMetadata(
            intent=llm_result.intent.value,
            processing_time_ms=processing_time
        )
    )


def _map_clarification_response(message: str):
    """Map clarification responses (A/B/C) to intents."""
    from typing import Optional
    msg = message.strip().lower()
    
    # Direct letter mapping
    if msg in ("a", "a)", "(a)", "option a"):
        return Intent.INVENTORY_SEARCH
    if msg in ("b", "b)", "(b)", "option b"):
        return Intent.SIMILAR_VEHICLES
    if msg in ("c", "c)", "(c)", "option c"):
        return Intent.PAYMENT_ESTIMATE
    
    # Keyword fallback for longer responses
    if "inventory" in msg or "search" in msg or "find" in msg:
        return Intent.INVENTORY_SEARCH
    if "similar" in msg:
        return Intent.SIMILAR_VEHICLES
    if "payment" in msg or "estimate" in msg:
        return Intent.PAYMENT_ESTIMATE
    
    return None


async def _route_intent(llm_result: LLMResult, original_message: str, session_id: str) -> tuple[str, list]:
    """Route the classified intent to the appropriate tool handler."""
    
    intent = llm_result.intent
    entities = llm_result.entities
    tool_calls = []
    
    if intent == Intent.GREETING:
        return (
            "Hello! I'm your Mini-Lakebed assistant. I can help you:\n\n"
            "🚗 **Search our inventory** - \"Show me SUVs under $35,000\"\n"
            "🔍 **Find similar vehicles** - \"Show me cars like the Toyota Camry\"\n"
            "💰 **Estimate payments** - \"What's the payment on a $25,000 car?\"\n\n"
            "What would you like to know?",
            []
        )
    
    elif intent == Intent.INVENTORY_SEARCH:
        return await _handle_inventory_search(entities, tool_calls, session_id)
    
    elif intent == Intent.VEHICLE_DETAILS:
        return await _handle_vehicle_details(entities, tool_calls, session_id)
    
    elif intent == Intent.SIMILAR_VEHICLES:
        return await _handle_similar_vehicles(entities, tool_calls, original_message, session_id)
    
    elif intent == Intent.PAYMENT_INQUIRY:
        # T02: Payment inquiry triggers SB 766 compliance check
        return await _handle_payment_inquiry(entities, tool_calls, session_id)

    elif intent == Intent.PAYMENT_ESTIMATE:
        return await _handle_payment_estimate(entities, tool_calls, session_id)
    
    elif intent == Intent.CREDIT_PREQUALIFICATION:
        return await _handle_credit_prequalification(entities, tool_calls, session_id)

    elif intent == Intent.OUT_OF_SCOPE:
        return (
            "I appreciate your question, but that's outside what I can help with. "
            "I'm specialized in:\n\n"
            "- Searching our vehicle inventory\n"
            "- Finding similar vehicles\n"
            "- Providing payment estimates\n\n"
            "Would you like help with any of those?",
            []
        )
    
    else:  # CLARIFICATION
        from app.services.session_context import update_awaiting_input
        await update_awaiting_input(session_id, "clarification")
        return (
            "I want to make sure I understand correctly. Are you asking about:\n\n"
            "**A)** Finding vehicles in our inventory\n"
            "**B)** Finding similar vehicles\n"
            "**C)** Estimating monthly payments\n\n"
            "Please let me know which one!",
            []
        )



async def _handle_inventory_search(entities, tool_calls, session_id: str) -> tuple[str, list]:
    """Handle inventory search intent."""
    
    from app.services.session_context import update_recent_vehicles
    
    # Build query parameters
    conditions = ["status = ?"]
    params = ["available"]
    
    if entities.make:
        conditions.append("LOWER(make) LIKE LOWER(?)")
        params.append(f"%{entities.make}%")
    
    if entities.model:
        conditions.append("LOWER(model) LIKE LOWER(?)")
        params.append(f"%{entities.model}%")
    
    if entities.min_year:
        conditions.append("year >= ?")
        params.append(entities.min_year)
    
    if entities.max_year:
        conditions.append("year <= ?")
        params.append(entities.max_year)
    
    if entities.min_price:
        conditions.append("price >= ?")
        params.append(entities.min_price)
    
    if entities.max_price:
        conditions.append("price <= ?")
        params.append(entities.max_price)
    
    if entities.body_style:
        conditions.append("LOWER(body_style) = LOWER(?)")
        params.append(entities.body_style)
    
    if entities.max_mileage:
        conditions.append("mileage <= ?")
        params.append(entities.max_mileage)
    
    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT id, make, model, year, trim, price, mileage, body_style, status
        FROM inventory 
        WHERE {where_clause}
        ORDER BY price ASC
        LIMIT 100
    """
    
    results = await execute_query(query, tuple(params))
    
    # Save search results to session context for later reference
    if results:
        await update_recent_vehicles(session_id, results)
    
    # Record tool call for frontend
    tool_calls.append(ToolCall(
        tool="search_inventory",
        params={
            "make": entities.make,
            "model": entities.model,
            "min_price": entities.min_price,
            "max_price": entities.max_price,
            "body_style": entities.body_style
        },
        results={"vehicles": results, "count": len(results)}
    ))
    
    if not results:
        return (
            "I couldn't find any vehicles matching those criteria. "
            "Try broadening your search—for example, increase the price range or include more body styles.",
            tool_calls
        )
    
    # Format response - structured card-style layout
    # Best practices: numbered, clear hierarchy, key info first, consistent spacing
    vehicle_cards = []
    for i, v in enumerate(results, 1):
        trim_display = f" {v['trim']}" if v['trim'] else ""
        mileage_display = f"{v['mileage']:,} mi" if v['mileage'] > 0 else "New"
        
        card = (
            f"**{i}. {v['year']} {v['make']} {v['model']}{trim_display}**\n"
            f"   💰 ${v['price']:,.0f}  •  📏 {mileage_display}  •  🚗 {v['body_style'].title()}"
        )
        vehicle_cards.append(card)
    
    vehicle_list = "\n\n".join(vehicle_cards)
    
    response = f"🔍 **Found {len(results)} vehicles** matching your criteria:\n\n---\n\n{vehicle_list}\n\n---\n\n💬 *Say a number (e.g., \"Tell me about #3\") for details, or ask about payments!*"
    
    if len(results) == 100:
        response += "\n\n⚠️ *Results limited to 100. Add filters to narrow your search.*"
    
    return response, tool_calls


async def _handle_vehicle_details(entities, tool_calls, session_id: str) -> tuple[str, list]:
    """Handle vehicle details intent."""
    
    from app.services.session_context import update_current_vehicle, resolve_vehicle_reference
    
    vehicle = None
    
    # First, check for pronoun/numbered references like "#3", "the first one", "that one"
    if entities.vehicle_reference:
        vehicle_ref = await resolve_vehicle_reference(session_id, entities.vehicle_reference)
        if vehicle_ref:
            # Re-fetch full details from DB to ensure we have all columns (color, engine, etc.)
            # The session context might only have partial data from search results
            vehicle = await execute_one(
                "SELECT * FROM inventory WHERE id = ?",
                (vehicle_ref['id'],)
            )
            if vehicle:
                # Update current vehicle context
                await update_current_vehicle(session_id, vehicle)
    
    # Try to find by ID if no reference match
    if not vehicle and entities.vehicle_id:
        vehicle = await execute_one(
            "SELECT * FROM inventory WHERE id = ?",
            (entities.vehicle_id,)
        )
    
    # If no ID, try to find by make/model/year
    if not vehicle and (entities.make or entities.model):
        conditions = ["status = 'available'"]
        params = []
        
        if entities.make:
            conditions.append("LOWER(make) LIKE LOWER(?)")
            params.append(f"%{entities.make}%")
        
        if entities.model:
            conditions.append("LOWER(model) LIKE LOWER(?)")
            params.append(f"%{entities.model}%")
        
        if entities.min_year:
            conditions.append("year = ?")
            params.append(entities.min_year)
        
        where_clause = " AND ".join(conditions)
        vehicle = await execute_one(
            f"SELECT * FROM inventory WHERE {where_clause} LIMIT 1",
            tuple(params)
        )
    
    if not vehicle:
        return (
            "I couldn't find that vehicle. "
            "Try describing it differently, like: \"Tell me about the 2024 Chevrolet Tahoe\"",
            []
        )
    
    # Save this vehicle as the "current" vehicle in session context
    await update_current_vehicle(session_id, vehicle)
    
    tool_calls.append(ToolCall(
        tool="get_vehicle",
        params={"vehicle_id": vehicle['id'], "make": entities.make, "model": entities.model},
        results={"vehicle": vehicle}
    ))
    
    response = f"""**{vehicle['year']} {vehicle['make']} {vehicle['model']} {vehicle['trim'] or ''}**

📍 **Price:** ${vehicle['price']:,.0f}
📏 **Mileage:** {vehicle['mileage']:,} miles
🎨 **Color:** {vehicle['exterior_color']} / {vehicle['interior_color']}
⛽ **Fuel:** {vehicle['fuel_type']} | **Transmission:** {vehicle['transmission']}
🔧 **Drivetrain:** {vehicle['drivetrain']} | **Engine:** {vehicle['engine']}

Would you like me to estimate the monthly payment for this vehicle?"""
    
    from app.services.session_context import update_awaiting_input

    # Set state so we know to interpret "Yes" as "Calculate payment"
    await update_awaiting_input(session_id, "confirm_payment_estimate")
    
    return response, tool_calls


async def _handle_similar_vehicles(entities, tool_calls, original_message: str, session_id: str) -> tuple[str, list]:
    """Handle similar vehicles intent - uses vector search."""
    
    from app.services.vector_store import find_similar_vehicles, find_similar_by_text, get_index_count
    from app.services.session_context import update_recent_vehicles
    
    # Check if vector store has data
    index_count = await get_index_count()
    if index_count == 0:
        return (
            "The vehicle similarity index hasn't been built yet. "
            "Please ask an admin to run the indexing script, or try a regular inventory search instead.",
            []
        )
    
    # First, check if user mentioned a vehicle reference like "#3" or "the first one"
    reference_vehicle = None
    if entities.vehicle_reference:
        from app.services.session_context import resolve_vehicle_reference
        reference_vehicle = await resolve_vehicle_reference(session_id, entities.vehicle_reference)
    
    # If no reference match, try to find by make/model
    if not reference_vehicle and (entities.make or entities.model):
        conditions = ["status = 'available'"]
        params = []
        
        if entities.make:
            conditions.append("LOWER(make) LIKE LOWER(?)")
            params.append(f"%{entities.make}%")
        
        if entities.model:
            conditions.append("LOWER(model) LIKE LOWER(?)")
            params.append(f"%{entities.model}%")
        
        # Add year filter if specified (ensures "2019 Ford Edge" finds the 2019, not 2023)
        if entities.min_year:
            conditions.append("year = ?")
            params.append(entities.min_year)
        
        where_clause = " AND ".join(conditions)
        reference_vehicle = await execute_one(
            f"SELECT * FROM inventory WHERE {where_clause} LIMIT 1",
            tuple(params)
        )
    
    # Find similar vehicles
    if reference_vehicle:
        # Find vehicles similar to the reference
        similar = await find_similar_vehicles(
            reference_vehicle,
            n_results=5,
            exclude_id=reference_vehicle['id']
        )
        
        if not similar:
            return (
                f"I couldn't find vehicles similar to the {reference_vehicle['year']} "
                f"{reference_vehicle['make']} {reference_vehicle['model']}. "
                "Try a regular inventory search instead.",
                []
            )
        
        tool_calls.append(ToolCall(
            tool="find_similar_vehicles",
            params={
                "reference_vehicle": f"{reference_vehicle['year']} {reference_vehicle['make']} {reference_vehicle['model']}",
                "reference_id": reference_vehicle['id']
            },
            results={"similar_vehicles": similar, "count": len(similar)}
        ))
        
        # Save similar vehicles to context for pronoun resolution ("tell me about the first one")
        await update_recent_vehicles(session_id, similar)
        
        # Format response
        vehicle_list = "\n".join([
            f"• **{v['year']} {v['make']} {v['model']}** - "
            f"${v['price']:,.0f} | Similarity: {v['similarity_score']:.0%}"
            for v in similar[:5]
        ])
        
        response = (
            f"Based on the **{reference_vehicle['year']} {reference_vehicle['make']} {reference_vehicle['model']}**, "
            f"here are similar vehicles:\n\n{vehicle_list}\n\n"
            "Would you like details on any of these?"
        )
        
    else:
        # Use the message itself as a semantic query
        similar = await find_similar_by_text(original_message, n_results=5)
        
        if not similar:
            return (
                "I couldn't find similar vehicles based on your description. "
                "Try being more specific, like: \"Show me vehicles similar to a Toyota Camry\"",
                []
            )
        
        tool_calls.append(ToolCall(
            tool="find_similar_by_text",
            params={"query": original_message},
            results={"similar_vehicles": similar, "count": len(similar)}
        ))
        
        # Save similar vehicles to context
        await update_recent_vehicles(session_id, similar)
        
        vehicle_list = "\n".join([
            f"• **{v['year']} {v['make']} {v['model']}** - "
            f"${v['price']:,.0f} | Match: {v['similarity_score']:.0%}"
            for v in similar[:5]
        ])
        
        response = f"Based on your description, here are matching vehicles:\n\n{vehicle_list}\n\n" \
                   "Would you like details on any of these?"
    
    return response, tool_calls


async def _handle_payment_inquiry(entities, tool_calls, session_id: str) -> tuple[str, list]:
    """
    Handle payment inquiry intent - implements SB 766 compliance.

    Per T02: Must show offering price before discussing payments.
    """
    from app.services.session_context import (
        get_current_vehicle, update_awaiting_input, record_disclosure, has_disclosure
    )
    from app.services.compliance_sentinel import (
        ComplianceSentinel, build_offering_price, format_offering_price_disclosure
    )
    from app.services.disclosure_tracker import record_offering_price

    # Get current vehicle from session context
    vehicle = await get_current_vehicle(session_id)

    if not vehicle:
        # No vehicle in context - need to identify one first
        return (
            "I'd be happy to help with payment information! "
            "First, which vehicle are you interested in?\n\n"
            "You can search our inventory or tell me about a specific vehicle you'd like to know about.",
            []
        )

    vehicle_id = vehicle.get("id")

    # T02: Check if offering price has been disclosed for this vehicle
    disclosed = await has_disclosure(session_id, vehicle_id, "offering_price")

    if not disclosed:
        # SB 766: Must show offering price first
        compliance = ComplianceSentinel()

        # Build and show offering price
        offering = await build_offering_price(vehicle)

        # Record disclosure in both session context and disclosure tracker
        await record_disclosure(session_id, vehicle_id, "offering_price", {
            "total": offering.total_offering_price,
            "base_price": offering.base_vehicle_price,
            "doc_fee": offering.doc_fee
        })
        await record_offering_price(
            session_id, vehicle_id, offering.total_offering_price, offering
        )

        # Log the compliance event
        await compliance._log_compliance_event(
            event_type="disclosure_presented",
            session_id=session_id,
            vehicle_id=vehicle_id,
            details={
                "disclosure_type": "offering_price",
                "total": offering.total_offering_price
            },
            regulatory_flags={"sb766_disclosure_verified": True}
        )

        tool_calls.append(ToolCall(
            tool="compliance_check",
            params={"check_type": "sb766_offering_price", "vehicle_id": vehicle_id},
            results={
                "disclosed": True,
                "offering_price": offering.total_offering_price,
                "components": offering.model_dump()
            }
        ))

        # Return offering price disclosure
        response = format_offering_price_disclosure(vehicle, offering)

        # Set state to expect payment details
        await update_awaiting_input(session_id, "payment_info")

        return response, tool_calls

    # Offering price already shown - prompt for payment details
    await update_awaiting_input(session_id, "payment_info")

    return (
        f"Great! To calculate the payment for this vehicle, I need a few details:\n\n"
        f"- Your credit score or credit range (excellent/good/fair)\n"
        f"- Your down payment amount\n\n"
        f"For example: \"I have good credit and $5,000 down\"",
        tool_calls
    )


async def _handle_payment_estimate(entities, tool_calls, session_id: str) -> tuple[str, list]:
    """Handle payment estimate intent."""

    from app.services.session_context import get_current_vehicle, update_last_payment, update_awaiting_input, clear_awaiting_input, record_disclosure, has_disclosure
    from app.services.compliance_sentinel import (
        ComplianceSentinel, build_offering_price, format_offering_price_disclosure
    )
    from app.services.disclosure_tracker import record_offering_price

    # Check for required information
    missing = []
    if not entities.fico_estimate and not entities.credit_tier:
        missing.append("your credit score or credit range (excellent/good/fair)")
    if not entities.down_payment:
        missing.append("your down payment amount")

    if missing:
        # Set awaiting_input state so we know what we're waiting for
        await update_awaiting_input(session_id, "payment_info")
        return (
            f"To calculate your payment, I need:\n\n"
            + "\n".join([f"• {m}" for m in missing]) +
            "\n\nFor example: \"I have good credit and $5,000 down\"",
            []
        )

    # Clear awaiting_input since we have what we need
    await clear_awaiting_input(session_id)

    # Get the currently discussed vehicle from session context
    context_vehicle = await get_current_vehicle(session_id)

    # T02: SB 766 Compliance Check - must disclose offering price before payment
    if context_vehicle:
        vehicle_id = context_vehicle.get("id")
        disclosed = await has_disclosure(session_id, vehicle_id, "offering_price")

        if not disclosed:
            # Must show offering price first
            compliance = ComplianceSentinel()
            offering = await build_offering_price(context_vehicle)

            # Record disclosure
            await record_disclosure(session_id, vehicle_id, "offering_price", {
                "total": offering.total_offering_price,
                "base_price": offering.base_vehicle_price,
                "doc_fee": offering.doc_fee
            })
            await record_offering_price(
                session_id, vehicle_id, offering.total_offering_price, offering
            )

            # Log the compliance event
            await compliance._log_compliance_event(
                event_type="disclosure_presented",
                session_id=session_id,
                vehicle_id=vehicle_id,
                details={"disclosure_type": "offering_price", "total": offering.total_offering_price},
                regulatory_flags={"sb766_disclosure_verified": True}
            )

            # Now proceed with payment calculation below (disclosure complete)
    
    if context_vehicle:
        # Use the vehicle the user was just discussing
        target_vehicle = context_vehicle
        vehicle_source = "context"
    else:
        # No vehicle in context - use a sample or ask user to select one
        target_vehicle = await execute_one(
            "SELECT * FROM inventory WHERE status = 'available' ORDER BY price LIMIT 1"
        )
        vehicle_source = "sample"
        
        if not target_vehicle:
            return "No vehicles available for payment calculation.", []
    
    vehicle_price = target_vehicle['price']
    down_payment = entities.down_payment or 0
    fico = entities.fico_estimate or _tier_to_fico(entities.credit_tier)
    term = entities.term_months or 60
    
    # Calculate LTV
    ltv = (vehicle_price - down_payment) / vehicle_price
    
    # Find matching rule
    from app.services.calculator import select_lender_rule
    rule = await select_lender_rule(fico, term, ltv)
    
    if not rule:
        return (
            f"I don't have approved rates for a FICO score of {fico} with a {term}-month term. "
            "Our demo lender rules cover credit scores 650+ with terms of 48, 60, or 72 months.",
            []
        )
    
    # Calculate payment
    from dataclasses import dataclass
    
    @dataclass
    class SimplePaymentResult:
        monthly_payment: float
        principal: float
        total_interest: float
        total_cost: float
    
    from app.services.calculator import calculate_monthly_payment
    
    loan_amount = vehicle_price - down_payment
    doc_fee = rule.get('doc_fee', 0) or 0
    principal = loan_amount + doc_fee
    
    monthly_payment = calculate_monthly_payment(principal, rule['base_apr'], term)
    total_cost = monthly_payment * term + down_payment
    total_interest = total_cost - vehicle_price - doc_fee
    
    result = SimplePaymentResult(
        monthly_payment=monthly_payment,
        principal=principal,
        total_interest=round(total_interest, 2),
        total_cost=round(total_cost, 2)
    )
    
    tool_calls.append(ToolCall(
        tool="estimate_payment",
        params={
            "vehicle_id": target_vehicle.get('id'),
            "vehicle_price": vehicle_price,
            "down_payment": down_payment,
            "fico": fico,
            "term_months": term,
            "vehicle_source": vehicle_source
        },
        results={
            "estimate": {
                "monthly_payment": result.monthly_payment,
                "apr": rule['base_apr'],
                "term_months": term,
                "principal": result.principal,
                "total_interest": result.total_interest,
                "total_cost": result.total_cost
            },
            "audit": {
                "rule_id": rule['rule_id'],
                "lender": rule['lender_name'],
                "ltv": round(ltv, 3)
            }
        }
    ))
    
    # Save payment result to context for recalculation ("What if I put $10k down instead?")
    await update_last_payment(session_id, {
        "vehicle": target_vehicle,
        "vehicle_price": vehicle_price,
        "down_payment": down_payment,
        "fico": fico,
        "term_months": term,
        "monthly_payment": result.monthly_payment,
        "apr": rule['base_apr'],
        "rule_id": rule['rule_id'],
        "lender": rule['lender_name']
    })
    
    # Build response with context awareness
    vehicle_desc = f"{target_vehicle['year']} {target_vehicle['make']} {target_vehicle['model']}"
    
    if vehicle_source == "context":
        intro = f"For the **{vehicle_desc}** you were looking at (${vehicle_price:,.0f}):"
    else:
        intro = f"Here's an estimate using our **{vehicle_desc}** at ${vehicle_price:,.0f}:\n\n" \
                "*(To calculate for a specific vehicle, first ask me about it)*"
    
    response = f"""💰 **Payment Estimate**

{intro}

📊 **Monthly Payment:** ${result.monthly_payment:,.2f}/mo
📈 **APR:** {rule['base_apr']}%
📅 **Term:** {term} months
💵 **Down Payment:** ${down_payment:,.0f}
🏦 **Total Interest:** ${result.total_interest:,.2f}

> 🔍 **Rule ID:** `{rule['rule_id']}` | **Lender:** {rule['lender_name']}

⚠️ *DEMO ONLY: Synthetic lender rules for demonstration purposes. Not a commitment to lend.*"""
    
    return response, tool_calls


def _tier_to_fico(tier: str) -> int:
    """Convert credit tier string to estimated FICO score."""
    mapping = {
        "super_prime": 780,
        "prime": 720,
        "near_prime": 670,
        "subprime": 600
    }
    return mapping.get(tier, 700)


async def _handle_credit_prequalification(entities, tool_calls, session_id: str) -> tuple[str, list]:
    """
    Handle credit prequalification intent - implements FCRA consent flow.

    Per T03: Must have FCRA consent before any credit evaluation.
    """
    from app.services.session_context import (
        get_current_vehicle, get_customer_id, set_customer_id,
        has_fcra_consent, set_fcra_consent, set_credit_status
    )
    from app.services.credit_officer import CreditOfficer, get_credit_tier
    from app.services.consent_manager import ConsentManager
    from app.models.credit import RequestedTerms
    import uuid

    # Get or create customer ID for this session
    customer_id = await get_customer_id(session_id)
    if not customer_id:
        customer_id = str(uuid.uuid4())
        await set_customer_id(session_id, customer_id)

    # Get current vehicle from session context
    vehicle = await get_current_vehicle(session_id)

    if not vehicle:
        # No vehicle in context - need to identify one first
        return (
            "I'd be happy to help with credit pre-qualification! "
            "First, which vehicle are you interested in?\n\n"
            "Search our inventory or tell me about a specific vehicle, "
            "then we can check what financing options you may qualify for.",
            []
        )

    # Check if FCRA consent exists
    consent_manager = ConsentManager()
    consent_check = await consent_manager.check_consent_valid(customer_id, "soft_pull")

    if not consent_check.valid:
        # FCRA consent required - trigger consent card
        tool_calls.append(ToolCall(
            tool="require_consent",
            params={
                "customer_id": customer_id,
                "consent_type": "soft_pull",
                "vehicle_id": vehicle.get("id")
            },
            results={
                "requires_consent": True,
                "message": "FCRA consent required before credit evaluation"
            }
        ))

        vehicle_desc = f"{vehicle['year']} {vehicle['make']} {vehicle['model']}"

        return (
            f"I'd be happy to check financing options for the **{vehicle_desc}**!\n\n"
            "Before I can do a soft credit check, I need your authorization. "
            "This is required by the Fair Credit Reporting Act (FCRA).\n\n"
            "**Important:** A soft pull will **not** affect your credit score.\n\n"
            "_Please review and accept the consent form to continue._",
            tool_calls
        )

    # Consent exists - check if we have credit info to evaluate
    # For demo, we'll use provided FICO or prompt for it
    fico_score = entities.fico_estimate

    if not fico_score:
        # Need credit info - prompt user
        tool_calls.append(ToolCall(
            tool="credit_check",
            params={
                "customer_id": customer_id,
                "vehicle_id": vehicle.get("id"),
                "consent_valid": True
            },
            results={
                "status": "awaiting_credit_info",
                "message": "Need FICO score to evaluate"
            }
        ))

        return (
            "Great! I have your authorization to proceed.\n\n"
            "For this demo, please tell me your approximate credit score, "
            "or describe your credit as excellent (750+), good (700-749), "
            "fair (650-699), or needs work (below 650).\n\n"
            "_Example: \"My credit score is around 720\" or \"I have good credit\"_",
            tool_calls
        )

    # We have consent and FICO - evaluate credit
    credit_officer = CreditOfficer()

    # Get vehicle price and calculate terms
    vehicle_price = vehicle.get("price", 30000)
    down_payment = entities.down_payment or 0
    term_months = entities.term_months or 60

    requested_terms = RequestedTerms(
        vehicle_price=vehicle_price,
        down_payment=down_payment,
        term_months=term_months
    )

    # Evaluate application
    decision = await credit_officer.evaluate_application(
        customer_id=customer_id,
        vehicle_id=vehicle.get("id"),
        fico_score=fico_score,
        requested_terms=requested_terms
    )

    # Store credit status in session
    await set_credit_status(session_id, {
        "decision": decision.decision,
        "tier": decision.tier.value,
        "fico_score": fico_score
    })

    tool_calls.append(ToolCall(
        tool="credit_evaluation",
        params={
            "customer_id": customer_id,
            "vehicle_id": vehicle.get("id"),
            "fico_score": fico_score,
            "down_payment": down_payment,
            "term_months": term_months
        },
        results={
            "decision": decision.decision,
            "tier": decision.tier.value,
            "approved_terms": decision.approved_terms.model_dump() if decision.approved_terms else None,
            "decline_reasons": [r.model_dump() for r in decision.decline_reasons] if decision.decline_reasons else None,
            "counter_offer": decision.counter_offer.model_dump() if decision.counter_offer else None
        }
    ))

    # Format response based on decision
    vehicle_desc = f"{vehicle['year']} {vehicle['make']} {vehicle['model']}"

    if decision.decision == "approved":
        terms = decision.approved_terms
        response = (
            f"**Great news!** You're pre-qualified for the **{vehicle_desc}**!\n\n"
            f"📊 **Credit Tier:** {decision.tier.value.replace('_', ' ').title()}\n"
            f"💰 **Monthly Payment:** ${terms.monthly_payment:,.2f}/mo\n"
            f"📈 **APR:** {terms.apr}%\n"
            f"📅 **Term:** {terms.term_months} months\n"
            f"💵 **Principal:** ${terms.principal:,.2f}\n\n"
            f"> 🏦 **Lender:** {terms.lender_name}\n\n"
            "⚠️ *This is a pre-qualification based on a soft credit pull. "
            "Final terms may vary based on full credit application.*"
        )

    elif decision.decision == "conditional":
        response = (
            f"**Conditional Pre-Qualification** for the **{vehicle_desc}**\n\n"
            f"📊 **Credit Tier:** {decision.tier.value.replace('_', ' ').title()}\n\n"
            "We can work with you! Here's what's needed:\n\n"
        )
        if decision.conditions:
            response += "\n".join([f"• {c}" for c in decision.conditions]) + "\n\n"

        if decision.counter_offer:
            offer = decision.counter_offer
            response += (
                f"**Counter-Offer:**\n"
                f"💵 Down payment: ${offer.required_down_payment:,.0f}\n"
                f"📈 APR: {offer.approved_apr}%\n"
                f"📅 Term: {offer.approved_term} months\n"
                f"💰 Monthly payment: ${offer.monthly_payment:,.2f}/mo\n\n"
            )

        response += "Would you like to proceed with these terms?"

    elif decision.decision == "declined":
        response = (
            f"**Pre-Qualification Result** for the **{vehicle_desc}**\n\n"
            "Unfortunately, we're unable to pre-qualify you at this time.\n\n"
            "**Principal Reasons:**\n"
        )
        if decision.decline_reasons:
            for reason in decision.decline_reasons[:4]:  # Max 4 per Reg B
                response += f"• {reason.text}\n"

        response += (
            f"\n> Bureau: {decision.bureau_source} | Date: {decision.score_date}\n\n"
            "You have the right to obtain a free copy of your credit report. "
            "If you have questions, please speak with our finance team."
        )

        if decision.counter_offer:
            offer = decision.counter_offer
            response += (
                f"\n\n**Alternative Option:**\n"
                f"{offer.message}"
            )

    else:
        response = "Unable to process credit evaluation at this time."

    return response, tool_calls
