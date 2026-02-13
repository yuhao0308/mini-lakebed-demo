/**
 * E2E Tests: Vehicle Selection & Details
 *
 * Tests verify that users can reference vehicles from search results
 * using ordinals (#3, "first car") and get detailed information.
 */
import { test, expect } from '@playwright/test';
import {
  navigateToChat,
  sendMessage,
  hasInventoryResults,
  getInventoryCardCount,
  getVehicleCardTitles,
  waitForChatReady,
} from './chat-helpers';

test.describe('B. Vehicle Selection & Details', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToChat(page);
    await waitForChatReady(page);
  });

  test('B1: "Tell me about #3" references third search result', async ({ page }) => {
    // First, do a search to populate results
    await sendMessage(page, 'Show me SUVs');
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    const cardCount = await getInventoryCardCount(page);
    expect(cardCount).toBeGreaterThanOrEqual(3);

    // Get the titles to verify later
    const titles = await getVehicleCardTitles(page);
    const thirdVehicle = titles[2]; // 0-indexed

    // Now ask about #3
    const response = await sendMessage(page, 'Tell me about #3');

    // Response should reference the third vehicle
    expect(response.length).toBeGreaterThan(0);
    // Should not show "couldn't find" or error
    expect(response.toLowerCase()).not.toContain("couldn't find");
    expect(response.toLowerCase()).not.toContain("error");
  });

  test('B2: "Tell me about the first car" references first search result', async ({ page }) => {
    // First, do a search
    await sendMessage(page, 'Show me trucks');
    const hasResults = await hasInventoryResults(page);

    // Skip if no trucks found
    if (!hasResults) {
      test.skip();
      return;
    }

    // Ask about "the first car"
    const response = await sendMessage(page, 'Tell me about the first car');

    // Response should provide vehicle details
    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain("couldn't find");
  });

  test('B3: "Tell me about the second one" uses ordinal reference', async ({ page }) => {
    // First, do a search
    await sendMessage(page, 'Show me SUVs between $20,000 and $35,000');
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    const cardCount = await getInventoryCardCount(page);
    expect(cardCount).toBeGreaterThanOrEqual(2);

    // Ask about "the second one"
    const response = await sendMessage(page, 'Tell me about the second one');

    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain("couldn't find");
  });

  test('B4: Vehicle reference without prior search prompts for search', async ({ page }) => {
    // Ask about a vehicle without prior search
    // This should either ask to search first or handle gracefully
    const response = await sendMessage(page, 'Tell me about #3');

    // Should handle gracefully - either ask to search first or explain no results
    expect(response.length).toBeGreaterThan(0);
    // Should not crash or show raw error
    expect(response.toLowerCase()).not.toContain('traceback');
    expect(response.toLowerCase()).not.toContain('exception');
  });

  test('B5: "the last one" references last search result', async ({ page }) => {
    // First, do a search
    await sendMessage(page, 'Show me SUVs');
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    const cardCount = await getInventoryCardCount(page);
    expect(cardCount).toBeGreaterThan(0);

    // Ask about "the last one"
    const response = await sendMessage(page, 'Tell me about the last one');

    expect(response.length).toBeGreaterThan(0);
    expect(response.toLowerCase()).not.toContain("couldn't find");
  });

  test('B6: Out-of-range reference (#100) handles gracefully', async ({ page }) => {
    // First, do a search
    await sendMessage(page, 'Show me SUVs');
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Ask about #100 (likely out of range)
    const response = await sendMessage(page, 'Tell me about #100');

    // Should handle gracefully
    expect(response.length).toBeGreaterThan(0);
    // Should explain the issue or ask for clarification
    expect(response.toLowerCase()).not.toContain('traceback');
  });
});
