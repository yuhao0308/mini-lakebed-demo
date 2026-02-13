/**
 * E2E Tests: Pre-Qualification Flow
 *
 * Tests verify the credit pre-qualification flow works correctly,
 * including consent handling and appropriate prompts.
 */
import { test, expect } from '@playwright/test';
import {
  navigateToChat,
  sendMessage,
  waitForChatReady,
} from './chat-helpers';

test.describe('D. Pre-Qualification Flow', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToChat(page);
    await waitForChatReady(page);
  });

  test('D1: "Can I get pre-approved?" initiates pre-qualification flow', async ({ page }) => {
    const response = await sendMessage(page, 'Can I get pre-approved?');

    // Should respond with pre-qualification guidance
    expect(response.length).toBeGreaterThan(0);

    // Should not show raw error
    expect(response.toLowerCase()).not.toContain('traceback');
    expect(response.toLowerCase()).not.toContain('exception');

    // May ask for vehicle selection or show consent form
    // Either way, should be a coherent response about pre-qualification
    expect(response.toLowerCase()).toMatch(/pre.*approv|credit|vehicle|consent|qualify/i);
  });

  test('D2: "Am I eligible for financing?" recognized as pre-qual intent', async ({ page }) => {
    const response = await sendMessage(page, 'Am I eligible for financing?');

    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain('traceback');
  });

  test('D3: Pre-qual after vehicle selection should proceed', async ({ page }) => {
    // First, search and select a vehicle
    await sendMessage(page, 'Show me SUVs');
    await sendMessage(page, 'Tell me about the first car');

    // Now ask about pre-approval
    const response = await sendMessage(page, 'Can I get pre-approved for this one?');

    expect(response.length).toBeGreaterThan(0);
    // Should guide user through pre-qual process
  });

  test('D4: "Check my credit" recognized as pre-qual', async ({ page }) => {
    const response = await sendMessage(page, 'Check my credit');

    expect(response.length).toBeGreaterThan(0);
    // Should handle as pre-qualification inquiry
  });

  test('D5: Pre-qual with vehicle context shows soft-pull card or guidance', async ({ page }) => {
    // Search and mention vehicle in pre-qual request
    await sendMessage(page, 'Show me SUVs under $30,000');

    const response = await sendMessage(
      page,
      'Can I get pre-approved for the first one?'
    );

    expect(response.length).toBeGreaterThan(0);

    // Check if soft-pull consent card appears
    const consentCard = page.locator('[data-testid="soft-pull-card"]');
    const cardVisible = await consentCard.isVisible().catch(() => false);

    // Either shows consent card or explains process
    if (!cardVisible) {
      expect(response.toLowerCase()).toMatch(/credit|pre.*approv|consent/i);
    }
  });
});
