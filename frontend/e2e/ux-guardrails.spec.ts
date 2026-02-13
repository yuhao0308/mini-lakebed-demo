/**
 * E2E Tests: Observability/UX Expectations
 *
 * Tests verify UX quality:
 * - Tool call indicators don't leak internal data
 * - "No results" only shown when truly empty
 * - UI remains responsive
 * - Messages render in correct order
 */
import { test, expect } from '@playwright/test';
import {
  navigateToChat,
  sendMessage,
  hasInventoryResults,
  waitForChatReady,
  getAssistantMessageCount,
} from './chat-helpers';

test.describe('F. Observability/UX Expectations', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToChat(page);
    await waitForChatReady(page);
  });

  test('F1: Tool badge shows friendly name, not raw JSON', async ({ page }) => {
    await sendMessage(page, 'Show me SUVs');

    // Check for tool results container
    const toolResults = page.locator('[data-testid^="tool-results-"]');
    const hasTools = await toolResults.count() > 0;

    if (hasTools) {
      // Get text content of tool badges
      const badges = page.locator('.tool-badge');
      const badgeCount = await badges.count();

      for (let i = 0; i < badgeCount; i++) {
        const badgeText = await badges.nth(i).textContent();
        // Should not contain raw JSON
        expect(badgeText).not.toContain('{');
        expect(badgeText).not.toContain('}');
        expect(badgeText).not.toContain('"');
      }
    }
  });

  test('F2: "No results" message only when truly no results', async ({ page }) => {
    const response = await sendMessage(page, 'Show me SUVs between $20,000 and $35,000');

    const hasResults = await hasInventoryResults(page);

    if (hasResults) {
      // If cards visible, response should NOT say "couldn't find"
      expect(response.toLowerCase()).not.toContain("couldn't find");
      expect(response.toLowerCase()).not.toContain("no vehicles");
    } else {
      // If no cards, response SHOULD acknowledge no results
      expect(response.toLowerCase()).toMatch(/couldn't find|no.*vehicle|no.*result/i);
    }
  });

  test('F3: UI remains responsive during query', async ({ page }) => {
    // Send a message
    const input = page.locator('[data-testid="chat-input"]');
    await input.fill('Show me SUVs');
    await page.click('[data-testid="chat-send-button"]');

    // Input should be disabled while loading
    await expect(input).toBeDisabled({ timeout: 2000 });

    // Wait for typing indicator
    const typingIndicator = page.locator('[data-testid="typing-indicator"]');
    await expect(typingIndicator).toBeVisible({ timeout: 5000 });

    // Wait for response
    await expect(typingIndicator).not.toBeVisible({ timeout: 60000 });

    // Input should be re-enabled after response
    await expect(input).toBeEnabled();
  });

  test('F4: Messages render in correct chronological order', async ({ page }) => {
    // Send multiple messages
    await sendMessage(page, 'Hello');
    await sendMessage(page, 'Show me SUVs');
    await sendMessage(page, 'Tell me about the first one');

    // Get all messages in order
    const messages = page.locator('[data-testid^="message-user-"], [data-testid^="message-assistant-"]');
    const count = await messages.count();

    // Should have at least 7 messages: initial greeting + 3 user + 3 assistant
    expect(count).toBeGreaterThanOrEqual(7);

    // Verify alternating pattern after initial greeting
    // Initial: assistant (greeting)
    // Then: user, assistant, user, assistant, user, assistant
    const firstUserIdx = 1; // Index of first user message

    for (let i = firstUserIdx; i < count; i++) {
      const testId = await messages.nth(i).getAttribute('data-testid');
      const expectedRole = (i - firstUserIdx) % 2 === 0 ? 'user' : 'assistant';
      expect(testId).toContain(expectedRole);
    }
  });

  test('F5: No duplicate assistant replies for single message', async ({ page }) => {
    const countBefore = await getAssistantMessageCount(page);

    await sendMessage(page, 'Show me trucks');

    const countAfter = await getAssistantMessageCount(page);

    // Should have exactly one more assistant message
    expect(countAfter).toBe(countBefore + 1);
  });

  test('F6: Inventory cards display all required information', async ({ page }) => {
    await sendMessage(page, 'Show me SUVs');
    const hasResults = await hasInventoryResults(page);

    if (hasResults) {
      const firstCard = page.locator('[data-testid="inventory-card-0"]');
      if (await firstCard.count()) {
        await expect(firstCard).toBeVisible();

        // Should have title (year make model)
        const title = firstCard.locator('[data-testid="vehicle-title"]');
        await expect(title).toBeVisible();
        const titleText = await title.textContent();
        expect(titleText).toMatch(/\d{4}/); // Contains year

        // Should have body style
        const bodyStyle = firstCard.locator('[data-testid="vehicle-body-style"]');
        await expect(bodyStyle).toBeVisible();

        // Should have price
        const price = firstCard.locator('.price-tag');
        await expect(price).toBeVisible();
        const priceText = await price.textContent();
        expect(priceText).toContain('$');
      } else {
        // Fallback rendering: inventory appears in markdown list format.
        const messageText =
          (await page
            .locator('[data-testid^="message-assistant-"]')
            .last()
            .locator('.message-bubble')
            .textContent()) || '';
        expect(messageText.toLowerCase()).toMatch(/found\s+\d+\s+vehicles/);
        expect(messageText).toMatch(/\$\d/);
        expect(messageText.toLowerCase()).toMatch(/suv|truck|sedan|coupe|van/);
      }
    }
  });

  test('F7: Assistant message contains markdown rendering', async ({ page }) => {
    await sendMessage(page, 'Show me SUVs between $20,000 and $35,000');

    // Get last assistant message
    const lastMessage = page.locator('[data-testid^="message-assistant-"]').last();
    const bubble = lastMessage.locator('.message-bubble');

    // Should render markdown (contains paragraph or list elements)
    const html = await bubble.innerHTML();
    expect(html).toMatch(/<p>|<li>|<strong>|<ul>|<ol>/);
  });

  test('F8: Typing indicator appears and disappears correctly', async ({ page }) => {
    const input = page.locator('[data-testid="chat-input"]');
    const typingIndicator = page.locator('[data-testid="typing-indicator"]');

    // Should not be visible initially
    await expect(typingIndicator).not.toBeVisible();

    // Send message
    await input.fill('Show me SUVs');
    await page.click('[data-testid="chat-send-button"]');

    // Should appear
    await expect(typingIndicator).toBeVisible({ timeout: 5000 });

    // Should disappear after response
    await expect(typingIndicator).not.toBeVisible({ timeout: 60000 });
  });

  test('F9: Chat scroll follows new messages', async ({ page }) => {
    // Send multiple messages
    await sendMessage(page, 'Show me SUVs');
    await sendMessage(page, 'Show me trucks');
    await sendMessage(page, 'Show me sedans');

    // Last message should be visible (scrolled into view)
    const lastMessage = page.locator('[data-testid^="message-assistant-"]').last();
    await expect(lastMessage).toBeInViewport();
  });

  test('F10: Session persists across messages', async ({ page }) => {
    // Search
    await sendMessage(page, 'Show me SUVs');
    const hasResults = await hasInventoryResults(page);
    expect(hasResults).toBe(true);

    // Reference previous results - should work if session persists
    const response = await sendMessage(page, 'Tell me about #1');

    // Should not say "no recent search" or similar
    expect(response.toLowerCase()).not.toContain('no recent');
    expect(response.toLowerCase()).not.toContain("haven't searched");
  });
});
