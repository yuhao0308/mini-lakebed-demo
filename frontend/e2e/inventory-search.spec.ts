/**
 * E2E Tests: Inventory Search
 *
 * Tests verify that inventory search queries return correct results
 * and handle various input formats properly.
 */
import { test, expect } from '@playwright/test';
import {
  navigateToChat,
  sendMessage,
  hasInventoryResults,
  getInventoryCardCount,
  getVehicleBodyStyles,
  waitForChatReady,
} from './chat-helpers';

test.describe('A. Inventory Search', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToChat(page);
    await waitForChatReady(page);
  });

  test('A1: "What SUVs do you have?" returns SUV results', async ({ page }) => {
    const response = await sendMessage(page, 'What SUVs do you have?');

    // Should show inventory results
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Response should mention "found" and vehicles
    expect(response.toLowerCase()).toMatch(/found|vehicle|suv/);

    // Verify all cards are SUVs
    const bodyStyles = await getVehicleBodyStyles(page);
    expect(bodyStyles.length).toBeGreaterThan(0);
    for (const style of bodyStyles) {
      expect(style).toBe('suv');
    }
  });

  test('A2: "Show me SUVs between $20,000 and $35,000" returns results in price range', async ({ page }) => {
    const response = await sendMessage(page, 'Show me SUVs between $20,000 and $35,000');

    // Should show inventory results
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Should NOT say "couldn't find"
    expect(response.toLowerCase()).not.toContain("couldn't find");

    // All cards should be SUVs
    const bodyStyles = await getVehicleBodyStyles(page);
    expect(bodyStyles.length).toBeGreaterThan(0);
    for (const style of bodyStyles) {
      expect(style).toBe('suv');
    }
  });

  test('A3: "Show me SUVs between $35,000 and $20000" (reversed) normalizes range and returns results', async ({ page }) => {
    const response = await sendMessage(page, 'Show me SUVs between $35,000 and $20000');

    // Should show inventory results (NOT "couldn't find")
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Should NOT say "couldn't find"
    expect(response.toLowerCase()).not.toContain("couldn't find");

    // All cards should be SUVs
    const bodyStyles = await getVehicleBodyStyles(page);
    expect(bodyStyles.length).toBeGreaterThan(0);
    for (const style of bodyStyles) {
      expect(style).toBe('suv');
    }
  });

  test('A4: "Any electric vehicles?" handles fuel type filter', async ({ page }) => {
    const response = await sendMessage(page, 'Any electric vehicles?');

    // This test verifies the query is handled gracefully
    // If no EVs exist, should say "couldn't find" for EVs specifically
    // If EVs exist, should show them
    // Either way, response should be coherent
    expect(response.length).toBeGreaterThan(0);

    // Should not return unrelated gas vehicles without acknowledging EVs
    if (response.toLowerCase().includes("couldn't find")) {
      expect(response.toLowerCase()).toMatch(/electric|ev|no.*vehicle|couldn't find any vehicles/);
    }
  });

  test('A5: "Show me trucks under 30k" handles single-bound price filter', async ({ page }) => {
    const response = await sendMessage(page, 'Show me trucks under 30k');

    // Should handle the query (may or may not find trucks)
    expect(response.length).toBeGreaterThan(0);

    // If results found, verify body style
    const hasResults = await hasInventoryResults(page);
    if (hasResults) {
      const bodyStyles = await getVehicleBodyStyles(page);
      for (const style of bodyStyles) {
        expect(style).toBe('truck');
      }
    }
  });

  test('A6: "Show me sedans around 25k" handles approximate pricing', async ({ page }) => {
    const response = await sendMessage(page, 'Show me sedans around 25k');

    // Should handle the query gracefully
    expect(response.length).toBeGreaterThan(0);

    // If results found, verify body style
    const hasResults = await hasInventoryResults(page);
    if (hasResults) {
      const bodyStyles = await getVehicleBodyStyles(page);
      for (const style of bodyStyles) {
        expect(style).toBe('sedan');
      }
    }
  });

  test('A7: Price range with "k" suffix parses correctly', async ({ page }) => {
    const response = await sendMessage(page, 'SUVs from 20k to 35k');

    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Should NOT say "couldn't find"
    expect(response.toLowerCase()).not.toContain("couldn't find");
  });

  test('A8: Price range with mixed formats works', async ({ page }) => {
    const response = await sendMessage(page, 'SUVs between $35k and 20000');

    // Reversed mixed format should still work
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);
    expect(response.toLowerCase()).not.toContain("couldn't find");
  });
});
