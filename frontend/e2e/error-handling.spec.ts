/**
 * E2E Tests: Error Handling & Guardrails
 *
 * Tests verify the system handles edge cases gracefully:
 * - Empty/nonsense input
 * - Contradictory input
 * - No infinite loops
 */
import { test, expect } from '@playwright/test';
import {
  navigateToChat,
  sendMessage,
  waitForChatReady,
  getAssistantMessageCount,
} from './chat-helpers';

test.describe('E. Error Handling & Guardrails', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToChat(page);
    await waitForChatReady(page);
  });

  test('E1: Empty input is prevented by UI', async ({ page }) => {
    const sendButton = page.locator('[data-testid="chat-send-button"]');

    // Button should be disabled with empty input
    await expect(sendButton).toBeDisabled();

    // Try typing spaces only
    const input = page.locator('[data-testid="chat-input"]');
    await input.fill('   ');

    // Button should still be disabled (whitespace-only)
    await expect(sendButton).toBeDisabled();
  });

  test('E2: Nonsense input returns helpful clarification', async ({ page }) => {
    const response = await sendMessage(page, 'asdfghjkl qwerty zxcvbn');

    expect(response.length).toBeGreaterThan(0);
    // Should not crash
    expect(response.toLowerCase()).not.toContain('traceback');
    expect(response.toLowerCase()).not.toContain('exception');
    // Should ask for clarification or explain it didn't understand
    expect(response.toLowerCase()).toMatch(/help|clarif|understand|assist|search|vehicle/i);
  });

  test('E3: Contradictory price range (min > max explicitly impossible) handles gracefully', async ({ page }) => {
    // Test with explicit "minimum $50k maximum $20k" phrasing
    const response = await sendMessage(page, 'Show me cars with minimum price $50,000 and maximum $20,000');

    expect(response.length).toBeGreaterThan(0);
    // Should normalize or ask for clarification, not error
    expect(response.toLowerCase()).not.toContain('traceback');
  });

  test('E4: Missing numbers in price query handles gracefully', async ({ page }) => {
    const response = await sendMessage(page, 'Show me SUVs between and dollars');

    expect(response.length).toBeGreaterThan(0);
    // Should ask for clarification or try to help
    expect(response.toLowerCase()).not.toContain('traceback');
  });

  test('E5: Payment query without vehicle context asks for vehicle', async ({ page }) => {
    const response = await sendMessage(page, "What's the monthly payment?");

    expect(response.length).toBeGreaterThan(0);
    // Should ask user to specify vehicle
    expect(response.toLowerCase()).toMatch(/vehicle|which|search|car/i);
  });

  test('E6: No infinite clarification loops', async ({ page }) => {
    // Send ambiguous message
    const response1 = await sendMessage(page, "What's the payment?");
    const count1 = await getAssistantMessageCount(page);

    // Provide clarification
    const response2 = await sendMessage(page, 'Show me SUVs first');
    const count2 = await getAssistantMessageCount(page);

    // Provide more info
    const response3 = await sendMessage(page, "What's the payment on the first one? good credit, $3000 down");
    const count3 = await getAssistantMessageCount(page);

    // Should not be stuck in a loop asking the same question
    // Count should increase by 1 each time (one assistant response per user message)
    expect(count2).toBe(count1 + 1);
    expect(count3).toBe(count2 + 1);

    // Final response should not be asking for the same info we just provided
    if (response3.toLowerCase().includes('credit')) {
      // If still asking about credit, it should be a different aspect
      expect(response3.toLowerCase()).not.toMatch(/what.*credit.*score|tell.*credit/i);
    }
  });

  test('E7: Very long message handles gracefully', async ({ page }) => {
    const longMessage = 'Show me SUVs '.repeat(50);
    const response = await sendMessage(page, longMessage);

    expect(response.length).toBeGreaterThan(0);
    // Should not crash
    expect(response.toLowerCase()).not.toContain('traceback');
  });

  test('E8: Special characters in message handled', async ({ page }) => {
    const response = await sendMessage(page, "Show me SUVs under $30,000! @#$%");

    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain('traceback');
  });

  test('E9: SQL injection attempt is safe', async ({ page }) => {
    const response = await sendMessage(page, "Show me SUVs'; DROP TABLE inventory; --");

    expect(response.length).toBeGreaterThan(0);
    // Should handle safely, not crash
    expect(response.toLowerCase()).not.toContain('traceback');
    // Should not show SQL error
    expect(response.toLowerCase()).not.toContain('sql');
    expect(response.toLowerCase()).not.toContain('syntax error');
  });

  test('E10: Repeated same message does not cause issues', async ({ page }) => {
    const message = 'Show me SUVs';

    const response1 = await sendMessage(page, message);
    const response2 = await sendMessage(page, message);

    // Both should work
    expect(response1.length).toBeGreaterThan(0);
    expect(response2.length).toBeGreaterThan(0);
    expect(response1.toLowerCase()).not.toContain('traceback');
    expect(response2.toLowerCase()).not.toContain('traceback');
  });
});
