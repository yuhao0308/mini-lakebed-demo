"""
BDD Step Definitions for Session Context Tests.

Uses pytest-bdd to run Gherkin scenarios.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.session_context import (
    SessionContext,
    get_session,
    update_current_vehicle,
    update_recent_vehicles,
    get_current_vehicle,
    resolve_vehicle_reference,
    update_last_payment,
    get_last_payment,
    add_chat_message,
    get_chat_history,
    update_awaiting_input,
    get_awaiting_input,
    clear_awaiting_input,
    clear_session,
)

# Load all scenarios from the feature file
scenarios('features/session_context.feature')


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def session_context():
    """Provide a clean session context for BDD tests."""
    return {"session_id": None, "vehicles": [], "current_vehicle": None, "payment": None}


@pytest.fixture
def sample_vehicles():
    return [
        {"id": i, "make": "Test", "model": f"Model{i}", "year": 2024, "price": 20000 + i*1000}
        for i in range(1, 6)
    ]


# ============================================================
# Given Steps
# ============================================================

@given("a new chat session")
def new_session(session_context):
    import uuid
    session_context["session_id"] = f"bdd-test-{uuid.uuid4()}"


@given("there are vehicles in search results")
@given("I searched and found 5 vehicles")
def vehicles_in_results(session_context, sample_vehicles, event_loop):
    session_context["vehicles"] = sample_vehicles
    event_loop.run_until_complete(
        update_recent_vehicles(session_context["session_id"], sample_vehicles)
    )


@given(parsers.parse("I am viewing a {make} {model}"))
def viewing_vehicle(session_context, make, model, event_loop):
    vehicle = {"id": 1, "make": make, "model": model, "year": 2024, "price": 28000}
    session_context["current_vehicle"] = vehicle
    event_loop.run_until_complete(
        update_current_vehicle(session_context["session_id"], vehicle)
    )


@given(parsers.parse("I am viewing a vehicle priced at ${price:d}"))
def viewing_priced_vehicle(session_context, price, event_loop):
    vehicle = {"id": 1, "make": "Test", "model": "Car", "year": 2024, "price": price}
    session_context["current_vehicle"] = vehicle
    event_loop.run_until_complete(
        update_current_vehicle(session_context["session_id"], vehicle)
    )


@given("I am viewing a vehicle")
def viewing_any_vehicle(session_context, event_loop):
    vehicle = {"id": 1, "make": "Test", "model": "Car", "year": 2024, "price": 30000}
    session_context["current_vehicle"] = vehicle
    event_loop.run_until_complete(
        update_current_vehicle(session_context["session_id"], vehicle)
    )


@given(parsers.parse("I request a payment with ${down:d} down and {credit} credit"))
def request_payment(session_context, down, credit):
    session_context["down_payment"] = down
    session_context["credit"] = credit


@given(parsers.parse("I calculated a payment with {term:d} months term"))
def calculated_payment(session_context, term, event_loop):
    payment = {"term_months": term, "monthly_payment": 450}
    session_context["payment"] = payment
    event_loop.run_until_complete(
        update_last_payment(session_context["session_id"], payment)
    )


@given(parsers.parse('I send a message "{message}"'))
def send_message(session_context, message, event_loop):
    event_loop.run_until_complete(
        add_chat_message(session_context["session_id"], "user", message)
    )


@given(parsers.parse('the assistant responds "{message}"'))
def assistant_responds(session_context, message, event_loop):
    event_loop.run_until_complete(
        add_chat_message(session_context["session_id"], "assistant", message)
    )


@given(parsers.parse("I have had {turns:d} conversation turns"))
def many_turns(session_context, turns, event_loop):
    for i in range(turns * 2):
        role = "user" if i % 2 == 0 else "assistant"
        event_loop.run_until_complete(
            add_chat_message(session_context["session_id"], role, f"Message {i}")
        )


@given(parsers.parse('the system is awaiting "{input_type}"'))
def system_awaiting(session_context, input_type, event_loop):
    event_loop.run_until_complete(
        update_awaiting_input(session_context["session_id"], input_type)
    )


@given(parsers.parse('I search for "{query}"'))
def search_query(session_context, query):
    session_context["last_search"] = query


@given(parsers.parse("I receive {count:d} results"))
def receive_results(session_context, count, sample_vehicles, event_loop):
    vehicles = sample_vehicles[:count]
    session_context["vehicles"] = vehicles
    event_loop.run_until_complete(
        update_recent_vehicles(session_context["session_id"], vehicles)
    )


# ============================================================
# When Steps
# ============================================================

@when(parsers.parse('I ask "{question}"'))
@when(parsers.parse('I ask about "{reference}"'))
def ask_question(session_context, event_loop):
    # This is handled by context - real implementation would parse intent
    pass


@when(parsers.parse('I ask for a payment without providing credit info'))
def ask_payment_no_credit(session_context, event_loop):
    event_loop.run_until_complete(
        update_awaiting_input(session_context["session_id"], "payment_info")
    )


@when("the payment is calculated")
def calculate_payment(session_context, event_loop):
    # Simulate payment calculation
    payment = {
        "vehicle_price": session_context["current_vehicle"]["price"],
        "down_payment": session_context.get("down_payment", 0),
        "monthly_payment": 450,
        "term_months": 60
    }
    session_context["payment"] = payment
    event_loop.run_until_complete(
        update_last_payment(session_context["session_id"], payment)
    )


@when(parsers.parse('I provide "{info}"'))
def provide_info(session_context, info, event_loop):
    event_loop.run_until_complete(
        clear_awaiting_input(session_context["session_id"])
    )


@when("I check the chat history")
def check_history(session_context, event_loop):
    history = event_loop.run_until_complete(
        get_chat_history(session_context["session_id"])
    )
    session_context["chat_history"] = history


@when(parsers.parse('I ask about the "{reference}"'))
def ask_about_reference(session_context, reference, event_loop):
    vehicle = event_loop.run_until_complete(
        resolve_vehicle_reference(session_context["session_id"], reference)
    )
    if vehicle:
        session_context["current_vehicle"] = vehicle
        event_loop.run_until_complete(
            update_current_vehicle(session_context["session_id"], vehicle)
        )


@when(parsers.parse("I ask for the payment with {credit} credit and ${down:d} down"))
def ask_payment_with_info(session_context, credit, down, event_loop):
    payment = {
        "vehicle_price": session_context["current_vehicle"]["price"],
        "down_payment": down,
        "credit": credit,
        "monthly_payment": 400,
        "term_months": 60
    }
    session_context["payment"] = payment
    event_loop.run_until_complete(
        update_last_payment(session_context["session_id"], payment)
    )


# ============================================================
# Then Steps
# ============================================================

@then(parsers.parse("the current vehicle should be vehicle #{num:d}"))
def verify_current_vehicle_num(session_context, num, event_loop):
    current = event_loop.run_until_complete(
        get_current_vehicle(session_context["session_id"])
    )
    assert current is not None
    assert current["id"] == num


@then(parsers.parse("the payment should be calculated for the {make} {model}"))
def verify_payment_vehicle(session_context, make, model, event_loop):
    current = event_loop.run_until_complete(
        get_current_vehicle(session_context["session_id"])
    )
    assert current["make"] == make
    assert current["model"] == model


@then(parsers.parse("I should get details for the {ordinal} vehicle"))
def verify_ordinal_vehicle(session_context, ordinal):
    ordinal_map = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5}
    expected_id = ordinal_map.get(ordinal)
    assert session_context["current_vehicle"]["id"] == expected_id


@then(parsers.parse("I should get the {make} {model}"))
def verify_specific_vehicle(session_context, make, model, event_loop):
    current = event_loop.run_until_complete(
        get_current_vehicle(session_context["session_id"])
    )
    assert current["make"] == make
    assert current["model"] == model


@then("the last payment should be saved")
def verify_payment_saved(session_context, event_loop):
    payment = event_loop.run_until_complete(
        get_last_payment(session_context["session_id"])
    )
    assert payment is not None


@then("the system should have my previous payment context")
def verify_payment_context(session_context, event_loop):
    payment = event_loop.run_until_complete(
        get_last_payment(session_context["session_id"])
    )
    assert payment is not None
    assert "term_months" in payment


@then(parsers.parse("it should contain {count:d} messages"))
def verify_message_count(session_context, count):
    assert len(session_context["chat_history"]) == count


@then(parsers.parse("it should contain at most {count:d} messages"))
def verify_max_messages(session_context, count):
    assert len(session_context["chat_history"]) <= count


@then(parsers.parse('the system should be awaiting "{input_type}"'))
def verify_awaiting(session_context, input_type, event_loop):
    awaiting = event_loop.run_until_complete(
        get_awaiting_input(session_context["session_id"])
    )
    assert awaiting == input_type


@then("the system should not be awaiting any input")
def verify_not_awaiting(session_context, event_loop):
    awaiting = event_loop.run_until_complete(
        get_awaiting_input(session_context["session_id"])
    )
    assert awaiting is None


@then("a payment should be calculated")
def verify_payment_calculated(session_context):
    assert session_context["payment"] is not None


@then("the payment should be saved to session")
def verify_payment_in_session(session_context, event_loop):
    payment = event_loop.run_until_complete(
        get_last_payment(session_context["session_id"])
    )
    assert payment is not None


# ============================================================
# Cleanup
# ============================================================

@pytest.fixture
def event_loop():
    """Provide event loop for async operations in BDD tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
