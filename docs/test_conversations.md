# Frontend Test Conversations

This document contains test conversations to manually verify the Mini-Lakebed AI demo through the frontend chat interface.

## Prerequisites

1. **Start the backend**:
   ```bash
   cd mini-lakebed-demo
   source venv/bin/activate
   cd backend && uvicorn app.main:app --reload --port 8000
   ```

2. **Start the frontend**:
   ```bash
   cd mini-lakebed-demo/frontend
   npm run dev
   ```

3. **Ensure Ollama is running** (optional for LLM, fallback rules work without it):
   ```bash
   ollama serve
   ```

---

## Test Suite 1: Inventory Search

### 1.1 Basic Search
**User**: Show me your available vehicles

**Expected**: List of all available inventory with prices and details

---

### 1.2 Filtered Search by Body Style
**User**: Show me SUVs

**Expected**: Only SUV body style vehicles displayed

---

### 1.3 Price Range Search
**User**: Show me vehicles under $30,000

**Expected**: Vehicles with price ≤ $30,000

---

### 1.4 Price Range with "k" notation
**User**: Show me cars between $20k and $35k

**Expected**: Vehicles with price between $20,000 and $35,000

---

### 1.5 Combined Filters
**User**: Show me Toyota SUVs under $40,000

**Expected**: Toyota brand, SUV body style, price ≤ $40,000

---

### 1.6 Make-Specific Search
**User**: What Chevrolet vehicles do you have?

**Expected**: Chevrolet brand vehicles only

---

### 1.7 Year-Specific Search
**User**: Show me 2024 vehicles

**Expected**: Only 2024 model year vehicles

---

## Test Suite 2: Vehicle Details

### 2.1 Details by Reference Number
**Prerequisite**: Complete a search first (e.g., "Show me SUVs")

**User**: Tell me about #3

**Expected**: Full details of the 3rd vehicle from previous search

---

### 2.2 Details by Ordinal
**Prerequisite**: Complete a search first

**User**: Tell me about the first one

**Expected**: Full details of the 1st vehicle from previous search

---

### 2.3 Details by Make/Model
**User**: Tell me about the 2024 Chevrolet Tahoe

**Expected**: Full details of matching vehicle including color, engine, drivetrain

---

### 2.4 Follow-up on "That One"
**Prerequisite**: Complete a search first

**User**: What about that one?

**Expected**: Details of the currently focused vehicle or prompt for clarification

---

## Test Suite 3: Similar Vehicles

### 3.1 Similar by Reference
**Prerequisite**: Complete a search first

**User**: Show me vehicles similar to #2

**Expected**: Vector similarity search results with match percentages

---

### 3.2 Similar by Description
**User**: Show me vehicles similar to a Toyota Camry

**Expected**: Vehicles similar to Toyota Camry based on features

---

### 3.3 Similar with Year Specification
**User**: Show me vehicles similar to the 2019 Ford Edge

**Expected**: Similar vehicles based on the 2019 Ford Edge specifically (not 2023)

---

## Test Suite 4: Payment Inquiry (SB 766 Compliance)

### 4.1 Payment Inquiry - No Vehicle Selected
**User**: What would the payment be?

**Expected**: Prompt to select a vehicle first

---

### 4.2 Payment Inquiry - Vehicle in Context
**Prerequisite**: First ask about a specific vehicle

**Conversation**:
1. **User**: Tell me about the 2024 Chevrolet Tahoe
2. **Assistant**: [Vehicle details + "Would you like me to estimate the monthly payment?"]
3. **User**: Yes, what's the payment?

**Expected**: SB 766 offering price disclosure shown BEFORE payment details are discussed

---

### 4.3 Payment Estimate with Credit Info
**Prerequisite**: Vehicle in context

**User**: I have good credit and $5,000 down

**Expected**: Full payment estimate with APR, term, monthly payment, lender info

---

### 4.4 Payment Estimate with FICO Score
**Prerequisite**: Vehicle in context

**User**: Calculate payment with 720 credit score and $10,000 down

**Expected**: Payment calculation using the provided FICO score

---

## Test Suite 5: Session Context Persistence

### 5.1 Context Across Messages
**Conversation**:
1. **User**: Show me trucks
2. **User**: Tell me about #1
3. **User**: What's the payment on it?

**Expected**: Each message should understand context from previous messages

---

### 5.2 Vehicle Reference After Payment
**Conversation**:
1. **User**: Tell me about the 2024 Toyota Camry
2. **User**: Yes [to calculate payment]
3. **User**: Show me similar vehicles

**Expected**: "Similar vehicles" should reference the Camry, not require re-specification

---

## Test Suite 6: Clarification Handling

### 6.1 Ambiguous Input
**User**: Help

**Expected**: Clarification options: A) Inventory B) Similar Vehicles C) Payments

---

### 6.2 Clarification Response
**Prerequisite**: Get clarification prompt

**User**: A

**Expected**: Routes to inventory search handler

---

## Test Suite 7: Greeting and Out-of-Scope

### 7.1 Greeting
**User**: Hello!

**Expected**: Friendly greeting with capability overview

---

### 7.2 Out-of-Scope
**User**: What's the weather today?

**Expected**: Polite decline with available capabilities listed

---

## Test Suite 8: T01 Data Foundation Verification

> **Note**: T01 added data models and tables, but the chat handlers don't actively use them yet. These tests verify the foundation exists.

### 8.1 Verify Compliance Logging (Backend Check)
When running payment inquiries, check the database:

```sql
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 5;
```

**Expected**: See entries for disclosure_presented events with SB 766 flags

---

### 8.2 Verify Tax Reference Data Loaded
```sql
SELECT COUNT(*) FROM tax_rates;
-- Should be >= 100
```

---

### 8.3 Verify Lender Programs Loaded
```sql  
SELECT COUNT(*) FROM lender_rules;
-- Should be >= 50
```

---

## Edge Cases to Test

### E.1 Empty Search Results
**User**: Show me Lamborghinis under $10,000

**Expected**: Friendly "no results found" message with suggestion to broaden search

---

### E.2 Invalid Credit Score
**User**: Calculate payment with 200 credit score

**Expected**: Handled gracefully (tier conversion or demo lender limitation message)

---

### E.3 Rapid Messages
Send multiple messages quickly without waiting for responses

**Expected**: UI should handle loading states gracefully, no duplicate messages

---

## Recording Test Results

| Test ID | Status | Notes |
|---------|--------|-------|
| 1.1     | ⬜     |       |
| 1.2     | ⬜     |       |
| 1.3     | ⬜     |       |
| ...     | ...    |       |

Status: ✅ Pass | ❌ Fail | ⬜ Not Tested

---

## Common Issues

1. **"Trouble connecting to the brain"**: Backend not running on port 8000
2. **Slow responses**: Ollama model loading (first request takes longer)
3. **Fallback classification**: If Ollama isn't running, regex fallback is used
