Feature: Session Context State Management
  As a chat user
  I want the system to remember key information during my session
  So that I can have natural, continuous conversations

  Background:
    Given a new chat session

  # ===== Current Vehicle Tracking =====
  
  Scenario: Current vehicle is set when viewing vehicle details
    Given there are vehicles in search results
    When I ask "tell me about #2"
    Then the current vehicle should be vehicle #2

  Scenario: Current vehicle persists for payment questions
    Given I am viewing a Toyota Camry
    When I ask "what's the payment?"
    Then the payment should be calculated for the Toyota Camry

  # ===== Recent Vehicles for Pronoun Resolution =====
  
  Scenario: User can reference vehicles by number
    Given I searched and found 5 vehicles
    When I ask about "#3"
    Then I should get details for the 3rd vehicle

  Scenario: User can reference vehicles by ordinal
    Given I searched and found 5 vehicles
    When I ask about "the first one"
    Then I should get details for the 1st vehicle

  Scenario: User can reference current vehicle with pronouns
    Given I am viewing a Honda Accord
    When I ask about "that one"
    Then I should get the Honda Accord

  # ===== Last Payment for Recalculation =====
  
  Scenario: Last payment is saved after calculation
    Given I am viewing a vehicle priced at $30000
    And I request a payment with $5000 down and good credit
    When the payment is calculated
    Then the last payment should be saved

  Scenario: User can ask "what if" questions about payment
    Given I calculated a payment with 60 months term
    When I ask "what if I did 72 months?"
    Then the system should have my previous payment context

  # ===== Chat History for Context =====
  
  Scenario: Chat history is maintained
    Given I send a message "Hello"
    And the assistant responds "Hi there!"
    When I check the chat history
    Then it should contain 2 messages

  Scenario: Chat history is trimmed to max turns
    Given I have had 15 conversation turns
    When I check the chat history
    Then it should contain at most 10 messages

  # ===== Awaiting Input State =====
  
  Scenario: System tracks when waiting for user input
    Given I am viewing a vehicle
    When I ask for a payment without providing credit info
    Then the system should be awaiting "payment_info"

  Scenario: Awaiting input is cleared when info is provided
    Given the system is awaiting "payment_info"
    When I provide "I have good credit and $5000 down"
    Then the system should not be awaiting any input

  # ===== Full Conversation Flow =====
  
  Scenario: Complete search to payment flow
    Given I search for "SUVs under $40000"
    And I receive 5 results
    When I ask about the "second one"
    And I ask for the payment with good credit and $3000 down
    Then the current vehicle should be vehicle #2
    And a payment should be calculated
    And the payment should be saved to session
