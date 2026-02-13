"""
LLM Service for intent classification and entity extraction.

Uses Ollama with llama3.2 for local inference.

T05: Added PII scrubbing for context passed to LLM.
"""

import httpx
import json
import re
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from app.middleware.pii_scrubber import get_pii_scrubber, ScrubbingResult

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    INVENTORY_SEARCH = "inventory_search"
    VEHICLE_DETAILS = "vehicle_details"
    SIMILAR_VEHICLES = "similar_vehicles"
    PAYMENT_ESTIMATE = "payment_estimate"
    PAYMENT_INQUIRY = "payment_inquiry"  # T02: Initial payment question (triggers SB 766 check)
    CREDIT_PREQUALIFICATION = "credit_prequalification"  # T03: Credit check / approval questions
    CLARIFICATION = "clarification"
    OUT_OF_SCOPE = "out_of_scope"
    GREETING = "greeting"


@dataclass
class ExtractedEntities:
    make: Optional[str] = None
    model: Optional[str] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    body_style: Optional[str] = None
    max_mileage: Optional[int] = None
    vehicle_id: Optional[int] = None
    vehicle_reference: Optional[str] = None  # For pronoun references like "#3", "the first one"
    down_payment: Optional[float] = None
    credit_tier: Optional[str] = None
    fico_estimate: Optional[int] = None
    term_months: Optional[int] = None


@dataclass
class LLMResult:
    intent: Intent
    entities: ExtractedEntities
    raw_response: str
    confidence: float = 0.8


OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3.1:8b"

SYSTEM_PROMPT = """You are an AI assistant for a car dealership demo system. Your job is to:
1. Classify the user's intent
2. Extract relevant entities from their message

Available intents:
- inventory_search: User wants to find/search for vehicles
- vehicle_details: User wants details about a specific vehicle
- similar_vehicles: User wants to find vehicles similar to one they mentioned
- payment_inquiry: User asks about payments without providing credit/down payment details
- payment_estimate: User wants to calculate monthly payments WITH credit and down payment info
- credit_prequalification: User asks about getting approved, prequalified, or credit check
- clarification: User's request is unclear
- out_of_scope: Request is outside our capabilities
- greeting: User is greeting or making small talk

Respond with a JSON object in this exact format:
{
  "intent": "inventory_search|vehicle_details|similar_vehicles|payment_inquiry|payment_estimate|credit_prequalification|clarification|out_of_scope|greeting",
  "entities": {
    "make": "string or null",
    "model": "string or null",
    "min_year": "number or null",
    "max_year": "number or null",
    "min_price": "number or null",
    "max_price": "number or null",
    "body_style": "sedan|suv|truck|coupe|van or null",
    "max_mileage": "number or null",
    "vehicle_id": "number or null",
    "vehicle_reference": "string or null (for references like '#3', 'the first one', 'that one')",
    "down_payment": "number or null",
    "credit_tier": "super_prime|prime|near_prime|subprime or null",
    "fico_estimate": "number or null",
    "term_months": "number or null"
  },
  "confidence": 0.0 to 1.0
}

ONLY output the JSON object, nothing else."""


async def classify_intent(user_message: str) -> LLMResult:
    """
    Use Ollama to classify intent and extract entities from user message.
    """
    if os.getenv("DEMO_FORCE_FALLBACK") == "1":
        return _fallback_classification(user_message)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": f"{SYSTEM_PROMPT}\n\nUser message: {user_message}",
                    "stream": False,
                    "format": "json"
                }
            )
            
            if response.status_code != 200:
                return _fallback_classification(user_message)
            
            result = response.json()
            raw_response = result.get("response", "{}")
            
            # Parse the JSON response
            parsed = json.loads(raw_response)
            
            intent_str = parsed.get("intent", "clarification")
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.CLARIFICATION
            
            entities_dict = parsed.get("entities", {})
            entities = ExtractedEntities(
                make=entities_dict.get("make"),
                model=entities_dict.get("model"),
                min_year=_safe_int(entities_dict.get("min_year")),
                max_year=_safe_int(entities_dict.get("max_year")),
                min_price=_safe_float(entities_dict.get("min_price")),
                max_price=_safe_float(entities_dict.get("max_price")),
                body_style=entities_dict.get("body_style"),
                max_mileage=_safe_int(entities_dict.get("max_mileage")),
                vehicle_id=_safe_int(entities_dict.get("vehicle_id")),
                vehicle_reference=entities_dict.get("vehicle_reference"),
                down_payment=_safe_float(entities_dict.get("down_payment")),
                credit_tier=entities_dict.get("credit_tier"),
                fico_estimate=_safe_int(entities_dict.get("fico_estimate")),
                term_months=_safe_int(entities_dict.get("term_months"))
            )

            # Normalize price range: LLM might return min > max if user said "between $35k and $20k"
            _normalize_price_range(entities)

            return LLMResult(
                intent=intent,
                entities=entities,
                raw_response=raw_response,
                confidence=parsed.get("confidence", 0.8)
            )
            
    except Exception as e:
        print(f"LLM error: {e}")
        return _fallback_classification(user_message)


def _fallback_classification(message: str) -> LLMResult:
    """
    Rule-based fallback when Ollama is unavailable.
    """
    message_lower = message.lower()
    
    # Payment keywords - distinguish between inquiry (simple) and estimate (with details)
    payment_keywords = ["payment", "monthly", "finance", "apr", "rate", "loan", "credit", "fico", "down payment"]
    if any(kw in message_lower for kw in payment_keywords):
        entities = _extract_payment_entities(message)

        # If user provided credit/FICO info or down payment, it's a full estimate request
        has_details = (
            entities.fico_estimate is not None or
            entities.credit_tier is not None or
            entities.down_payment is not None
        )

        if has_details:
            return LLMResult(
                intent=Intent.PAYMENT_ESTIMATE,
                entities=entities,
                raw_response="fallback",
                confidence=0.6
            )
        else:
            # Simple payment inquiry without details - triggers SB 766 check
            return LLMResult(
                intent=Intent.PAYMENT_INQUIRY,
                entities=entities,
                raw_response="fallback",
                confidence=0.6
            )

    # T03: Credit prequalification keywords
    credit_keywords = ["approved", "approve", "prequalify", "pre-qualify", "prequalification",
                       "qualify", "can i get", "am i eligible", "credit check", "check my credit",
                       "soft pull", "hard pull"]
    if any(kw in message_lower for kw in credit_keywords):
        return LLMResult(
            intent=Intent.CREDIT_PREQUALIFICATION,
            entities=ExtractedEntities(),
            raw_response="fallback",
            confidence=0.7
        )

    # Similar vehicles keywords - check FIRST so "similar like #3" works correctly
    similar_keywords = ["similar", "like this", "like that", "alternatives", "comparable", "same as", "resembles"]
    if any(kw in message_lower for kw in similar_keywords):
        entities = _extract_inventory_entities(message)
        # Also check for vehicle references like "#3" for "similar like #3"
        vehicle_ref = _extract_vehicle_reference(message)
        if vehicle_ref:
            entities.vehicle_reference = vehicle_ref
        return LLMResult(
            intent=Intent.SIMILAR_VEHICLES,
            entities=entities,
            raw_response="fallback",
            confidence=0.7
        )
    
    # Vehicle details - check for references like "#3", "the first one", "tell me about"
    vehicle_ref = _extract_vehicle_reference(message)
    if vehicle_ref:
        entities = _extract_inventory_entities(message)
        entities.vehicle_reference = vehicle_ref
        return LLMResult(
            intent=Intent.VEHICLE_DETAILS,
            entities=entities,
            raw_response="fallback",
            confidence=0.8
        )
    
    # Also check for explicit detail requests
    detail_keywords = ["tell me about", "details", "more info", "show me the", "what about"]
    if any(kw in message_lower for kw in detail_keywords):
        return LLMResult(
            intent=Intent.VEHICLE_DETAILS,
            entities=_extract_inventory_entities(message),
            raw_response="fallback",
            confidence=0.7
        )
    
    # Inventory keywords
    inventory_keywords = ["show", "find", "search", "looking", "have", "any", "under", "suv", "truck", "sedan", "car", "vehicle"]
    if any(kw in message_lower for kw in inventory_keywords):
        return LLMResult(
            intent=Intent.INVENTORY_SEARCH,
            entities=_extract_inventory_entities(message),
            raw_response="fallback",
            confidence=0.6
        )
    
    # Greeting keywords
    greeting_keywords = ["hello", "hi", "hey", "good morning", "good afternoon"]
    if any(kw in message_lower for kw in greeting_keywords):
        return LLMResult(
            intent=Intent.GREETING,
            entities=ExtractedEntities(),
            raw_response="fallback",
            confidence=0.9
        )
    
    return LLMResult(
        intent=Intent.CLARIFICATION,
        entities=ExtractedEntities(),
        raw_response="fallback",
        confidence=0.5
    )


def _extract_vehicle_reference(message: str) -> Optional[str]:
    """Extract vehicle reference like '#3', 'the first one', 'that one' from message."""
    message_lower = message.lower()
    
    # Check for numbered references: "#3", "number 3", "3rd", "about 3", or just "3"
    num_match = re.search(r'#(\d+)|number\s*(\d+)|(\d+)(?:st|nd|rd|th)|(?:about|vehicle|car)\s+(\d+)(?:\s|$)|^(\d+)$', message_lower)
    if num_match:
        num = num_match.group(1) or num_match.group(2) or num_match.group(3) or num_match.group(4) or num_match.group(5)
        return f"#{num}"
    
    # Check for ordinal references
    ordinals = ["first", "second", "third", "fourth", "fifth", "last"]
    for ordinal in ordinals:
        if ordinal in message_lower:
            return f"the {ordinal} one"
    
    # Check for pronoun references
    pronouns = ["that one", "this one", "it", "that car", "this car"]
    for pronoun in pronouns:
        if pronoun in message_lower:
            return pronoun
    
    return None




def _extract_inventory_entities(message: str) -> ExtractedEntities:
    """Extract inventory-related entities using regex patterns."""
    entities = ExtractedEntities()
    message_lower = message.lower()
    
    # Body style
    body_styles = ["suv", "truck", "sedan", "coupe", "van"]
    for style in body_styles:
        if style in message_lower:
            entities.body_style = style
            break
    
    # Price extraction - handle multiple patterns
    
    # Pattern 1: "between $X and $Y" or "from $X to $Y"
    between_match = re.search(
        r'(?:between|from)\s*\$?([\d,]+)\s*(k|thousand)?\s*(?:and|to|-)\s*\$?([\d,]+)\s*(k|thousand)?',
        message_lower
    )
    if between_match:
        price1 = _parse_price_with_suffix(between_match.group(1), between_match.group(2))
        price2 = _parse_price_with_suffix(between_match.group(3), between_match.group(4))
        # Normalize: ensure min <= max (user may say "between $35k and $20k")
        entities.min_price = min(price1, price2)
        entities.max_price = max(price1, price2)
    else:
        # Pattern 2: "$X-$Y" or "$Xk-$Yk" range format (e.g., "$20,000-$30,000" or "$20k-$30k")
        range_match = re.search(
            r'\$?([\d,]+)\s*(k|thousand)?\s*[-–—]\s*\$?([\d,]+)\s*(k|thousand)?',
            message_lower
        )
        if range_match:
            price1 = _parse_price_with_suffix(range_match.group(1), range_match.group(2))
            price2 = _parse_price_with_suffix(range_match.group(3), range_match.group(4))
            # Normalize: ensure min <= max
            entities.min_price = min(price1, price2)
            entities.max_price = max(price1, price2)
        else:
            # Pattern 3: "under $X" or "less than $X" or "below $X"
            under_match = re.search(
                r'(?:under|less than|below|up to|max|maximum)\s*\$?([\d,]+)\s*(k|thousand)?',
                message_lower
            )
            if under_match:
                entities.max_price = _parse_price_with_suffix(under_match.group(1), under_match.group(2))

            # Pattern 4: "over $X" or "more than $X" or "above $X"
            over_match = re.search(
                r'(?:over|more than|above|at least|min|minimum|starting at)\s*\$?([\d,]+)\s*(k|thousand)?',
                message_lower
            )
            if over_match:
                entities.min_price = _parse_price_with_suffix(over_match.group(1), over_match.group(2))
    
    # Make extraction
    makes = ["toyota", "honda", "ford", "chevrolet", "chevy", "nissan", "hyundai", "kia", "mazda", "subaru", "bmw", "mercedes", "audi"]
    for make in makes:
        if make in message_lower:
            entities.make = make.title()
            if make == "chevy":
                entities.make = "Chevrolet"
            break
    
    # Year extraction (e.g., "2024 Chevrolet" or "the 2023 Toyota")
    year_match = re.search(r'\b(20[1-2][0-9])\b', message_lower)
    if year_match:
        entities.min_year = int(year_match.group(1))  # Using min_year for exact year lookup
    
    # Model extraction - common models
    models = ["tahoe", "camry", "accord", "civic", "cr-v", "crv", "rav4", "tacoma", "f-150", "f150", 
              "mustang", "explorer", "edge", "escape", "hrv", "hr-v", "pilot", "odyssey", "traverse",
              "silverado", "equinox", "malibu", "altima", "rogue", "sentra", "sorento", "sportage",
              "tucson", "santa fe", "sonata", "elantra", "kona", "cx-5", "cx5", "mazda3", "outback"]
    for model in models:
        if model in message_lower:
            # Normalize model names
            model_normalized = model.upper().replace("-", "-")
            if model in ["crv", "cr-v"]:
                model_normalized = "CR-V"
            elif model in ["hrv", "hr-v"]:
                model_normalized = "HR-V"
            elif model in ["f150", "f-150"]:
                model_normalized = "F-150"
            elif model in ["cx-5", "cx5"]:
                model_normalized = "CX-5"
            else:
                model_normalized = model.title()
            entities.model = model_normalized
            break

    # Final safety check: normalize price range
    _normalize_price_range(entities)

    return entities


def _parse_price_with_suffix(price_str: str, suffix: Optional[str]) -> float:
    """
    Parse a price string with explicit suffix handling.
    
    Args:
        price_str: The numeric part (e.g., "20", "30,000")  
        suffix: The suffix if captured (e.g., "k", "thousand", None)
    
    Returns:
        Price as float in dollars
    """
    # Remove commas and convert to float
    price = float(price_str.replace(",", ""))
    
    # Apply multiplier based on suffix
    if suffix and suffix.lower() in ("k", "thousand"):
        price *= 1000
    # If no suffix and price is suspiciously low (< 1000), assume thousands
    elif price < 1000:
        price *= 1000
    
    return price


def _extract_payment_entities(message: str) -> ExtractedEntities:
    """Extract payment-related entities using regex patterns.

    Also extracts vehicle references and inventory entities since payment
    queries often include vehicle context like "first car" or "2020 Ford Bronco".
    """
    # Start with inventory entities (make, model, year, body_style)
    entities = _extract_inventory_entities(message)
    message_lower = message.lower()

    # Also check for vehicle references like "first car", "#3", "that one"
    vehicle_ref = _extract_vehicle_reference(message)
    if vehicle_ref:
        entities.vehicle_reference = vehicle_ref

    # Down payment - improved pattern to handle "$5,000 down" and "$5k down"
    down_match = re.search(r'\$?([\d,]+)\s*(k|thousand)?\s*down', message_lower)
    if down_match:
        down = float(down_match.group(1).replace(",", ""))
        if down_match.group(2) and down_match.group(2).lower() in ("k", "thousand"):
            down *= 1000
        elif down < 100:  # Assume thousands if small number
            down *= 1000
        entities.down_payment = down

    # Credit/FICO
    fico_match = re.search(r'(\d{3})\s*(credit|fico|score)?', message_lower)
    if fico_match:
        fico = int(fico_match.group(1))
        if 300 <= fico <= 850:
            entities.fico_estimate = fico

    # Credit tier keywords
    if "excellent" in message_lower or "super" in message_lower:
        entities.credit_tier = "super_prime"
    elif "good" in message_lower or "prime" in message_lower:
        entities.credit_tier = "prime"
    elif "fair" in message_lower or "near" in message_lower:
        entities.credit_tier = "near_prime"
    elif "poor" in message_lower or "bad" in message_lower:
        entities.credit_tier = "subprime"

    # Term months
    term_match = re.search(r'(\d{2})\s*month', message_lower)
    if term_match:
        entities.term_months = int(term_match.group(1))

    return entities


def _safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_price_range(entities: ExtractedEntities) -> None:
    """
    Normalize price range: ensure min_price <= max_price.

    Users may say "between $35,000 and $20,000" (reversed order).
    This swaps the values if min > max.

    Modifies entities in-place.
    """
    if entities.min_price is not None and entities.max_price is not None:
        if entities.min_price > entities.max_price:
            entities.min_price, entities.max_price = entities.max_price, entities.min_price


def scrub_context_for_llm(data: Dict[str, Any]) -> ScrubbingResult:
    """
    T05: Scrub PII from any context data before passing to LLM.

    Per spec §5.3: All data passed to LLM must go through PII scrubber.
    Always uses LOW clearance to ensure maximum protection.

    Args:
        data: Context data to scrub (vehicle info, customer data, etc.)

    Returns:
        ScrubbingResult with scrubbed_data and audit info
    """
    scrubber = get_pii_scrubber()
    result = scrubber.scrub_for_llm_context(data)

    if result.scrubbing_applied:
        logger.info(
            f"PII scrubbed from LLM context: {len(result.fields_scrubbed)} fields masked"
        )

    return result
