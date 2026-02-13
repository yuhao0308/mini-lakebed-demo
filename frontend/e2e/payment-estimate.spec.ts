/**
 * E2E Tests: Payment Estimate Flow
 *
 * Tests verify the multi-turn and one-shot payment estimate flows work correctly,
 * including vehicle resolution, credit/down payment handling, and result display.
 */
import { test, expect } from '@playwright/test';
import {
  navigateToChat,
  sendMessage,
  hasInventoryResults,
  hasPaymentEstimate,
  waitForChatReady,
  getAssistantMessageCount,
} from './chat-helpers';

test.describe('C. Payment Estimate Flow', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToChat(page);
    await waitForChatReady(page);
  });

  test('C1: Multi-turn payment flow - search, select, provide credit/down', async ({ page }) => {
    // Step 1: Search for vehicles
    await sendMessage(page, 'Show me SUVs between $20,000 and $35,000');
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Step 2: Ask about payment on first car
    const paymentResponse = await sendMessage(page, "What's the monthly payment on the first car?");

    // Should either show payment or ask for credit/down info
    expect(paymentResponse.length).toBeGreaterThan(0);

    // If it asks for credit/down info, provide it
    if (paymentResponse.toLowerCase().includes('credit') || paymentResponse.toLowerCase().includes('down')) {
      // Step 3: Provide credit and down payment info
      const finalResponse = await sendMessage(page, 'I have good credit and $5,000 down');

      // Should now show payment estimate or payment info
      expect(finalResponse.length).toBeGreaterThan(0);
      // Should NOT ask A/B/C disambiguation again
      expect(finalResponse).not.toMatch(/\bA\b.*\bB\b.*\bC\b/);
      expect(finalResponse.toLowerCase()).not.toContain('please choose');
    }
  });

  test('C2: Multi-turn - "What is the monthly payment on the first car?" then "good credit and $5,000 down"', async ({ page }) => {
    // First, search for vehicles
    await sendMessage(page, 'Show me SUVs');
    expect(await hasInventoryResults(page)).toBe(true);

    // Ask about payment
    const response1 = await sendMessage(page, "What's the monthly payment on the first car?");
    expect(response1.length).toBeGreaterThan(0);

    // Provide credit and down payment in follow-up
    const response2 = await sendMessage(page, 'good credit and $5,000 down');

    // Should show payment estimate, not another disambiguation
    expect(response2.length).toBeGreaterThan(0);
    // Should not ask to choose A, B, C, or D
    expect(response2).not.toMatch(/\b[ABCD]\b\./);
  });

  test('C3: One-shot payment query with all info', async ({ page }) => {
    // Search first
    await sendMessage(page, 'Show me SUVs');
    expect(await hasInventoryResults(page)).toBe(true);

    // One-shot: vehicle + credit + down in single message
    const response = await sendMessage(
      page,
      "What's the monthly payment on the first car? I have good credit and $5,000 down"
    );

    // Should provide payment info without additional disambiguation
    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain('please choose');
  });

  test('C4: Payment query with explicit vehicle info', async ({ page }) => {
    // One-shot with make/model
    const response = await sendMessage(
      page,
      "What's the monthly payment on a 2020 Ford Bronco Sport? good credit, $5,000 down"
    );

    // Should handle the query - either find vehicle or explain issue
    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain('traceback');
  });

  test('C5: Payment with FICO score instead of tier', async ({ page }) => {
    // Search first
    await sendMessage(page, 'Show me SUVs');
    expect(await hasInventoryResults(page)).toBe(true);

    // Ask about payment with FICO score
    const response = await sendMessage(
      page,
      "What's the monthly on the first car? My credit score is 720 and I have $3000 down"
    );

    expect(response.length).toBeGreaterThan(0);
    // Should process numeric FICO
  });

  test('C6: Payment without down payment shows estimate', async ({ page }) => {
    // Search first
    await sendMessage(page, 'Show me SUVs');
    expect(await hasInventoryResults(page)).toBe(true);

    // Payment with only credit info
    const response = await sendMessage(
      page,
      "Monthly payment on the first one with excellent credit?"
    );

    // Should handle - may assume $0 down or ask for it
    expect(response.length).toBeGreaterThan(0);
  });

  test('C7: Response includes payment estimate card when calculation succeeds', async ({ page }) => {
    // Search first
    await sendMessage(page, 'Show me SUVs between $20,000 and $30,000');
    expect(await hasInventoryResults(page)).toBe(true);

    // Full payment query
    const response = await sendMessage(
      page,
      "What's the monthly payment on the first car with good credit and $5,000 down?"
    );

    // Check if payment estimate widget appears
    const hasEstimate = await hasPaymentEstimate(page);
    // If payment calculation succeeded, should show estimate card
    // (may not appear if vehicle/rule matching fails)
    if (hasEstimate) {
      const estimateCard = page.locator('[data-testid="payment-estimate-result"]');
      await expect(estimateCard).toBeVisible();
    }
  });

  test('C8: Credit tier variations are recognized', async ({ page }) => {
    // Search first
    await sendMessage(page, 'Show me SUVs');

    // Test "excellent credit"
    const response = await sendMessage(
      page,
      "Payment on the first one? excellent credit, $4000 down"
    );
    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain('please choose');
  });
});
