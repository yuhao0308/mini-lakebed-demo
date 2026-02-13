/**
 * Shared helpers for chat E2E tests.
 */
import { Page, expect } from '@playwright/test';

async function getLastAssistantText(page: Page): Promise<string> {
  const messages = page.locator('[data-testid^="message-assistant-"]');
  const lastMessage = messages.last();
  const content = await lastMessage.locator('.message-bubble').textContent();
  return content || '';
}

/**
 * Navigate to chat view from any page.
 */
export async function navigateToChat(page: Page): Promise<void> {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.click('[data-testid="nav-chat"]');
  await expect(page.locator('[data-testid="chat-pane"]')).toBeVisible();
}

/**
 * Send a chat message and wait for response.
 * Returns the assistant's response text content.
 */
export async function sendMessage(page: Page, message: string): Promise<string> {
  const assistantMessages = page.locator('[data-testid^="message-assistant-"]');
  const assistantCountBefore = await assistantMessages.count();

  const input = page.locator('[data-testid="chat-input"]');
  await input.fill(message);
  await page.click('[data-testid="chat-send-button"]');

  // Wait for typing indicator when visible; some fast responses may skip the visible state.
  const typingIndicator = page.locator('[data-testid="typing-indicator"]');
  const sawTypingIndicator = await typingIndicator.isVisible().catch(() => false);
  if (sawTypingIndicator) {
    await expect(typingIndicator).not.toBeVisible({ timeout: 60000 });
  }

  // Always wait for a new assistant message to be appended.
  await expect
    .poll(async () => assistantMessages.count(), { timeout: 60000 })
    .toBeGreaterThan(assistantCountBefore);

  // Get the last assistant message
  const lastMessage = assistantMessages.last();
  await expect(lastMessage).toBeVisible();

  const content = await lastMessage.locator('.message-bubble').textContent();
  return content || '';
}

/**
 * Get the count of assistant messages in the chat.
 */
export async function getAssistantMessageCount(page: Page): Promise<number> {
  const messages = page.locator('[data-testid^="message-assistant-"]');
  return await messages.count();
}

/**
 * Get the count of inventory cards in the last tool result.
 */
export async function getInventoryCardCount(page: Page): Promise<number> {
  const results = page.locator('[data-testid="inventory-results"]').last();
  const cards = results.locator('[data-testid^="inventory-card-"]');
  const cardCount = await cards.count();
  if (cardCount > 0) {
    return cardCount;
  }

  const text = await getLastAssistantText(page);
  const numbered = text.match(/^\s*\d+\./gm);
  return numbered ? numbered.length : 0;
}

/**
 * Check if inventory results are visible in the chat.
 */
export async function hasInventoryResults(page: Page): Promise<boolean> {
  const results = page.locator('[data-testid="inventory-results"]');
  if ((await results.count()) > 0) {
    return true;
  }

  const text = await getLastAssistantText(page);
  return /found\s+\d+\s+vehicles/i.test(text) || /^\s*1\./m.test(text);
}

/**
 * Check if payment estimate result is visible.
 */
export async function hasPaymentEstimate(page: Page): Promise<boolean> {
  const result = page.locator('[data-testid="payment-estimate-result"]');
  const count = await result.count();
  return count > 0;
}

/**
 * Get the text content of all vehicle cards.
 */
export async function getVehicleCardTitles(page: Page): Promise<string[]> {
  const results = page.locator('[data-testid="inventory-results"]').last();
  const titles = results.locator('[data-testid="vehicle-title"]');
  const count = await titles.count();
  const titleTexts: string[] = [];
  for (let i = 0; i < count; i++) {
    const text = await titles.nth(i).textContent();
    if (text) titleTexts.push(text);
  }
  if (titleTexts.length > 0) {
    return titleTexts;
  }

  const markdownText = await getLastAssistantText(page);
  const lines = markdownText
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => /^\d+\.\s+/.test(line));

  for (const line of lines) {
    titleTexts.push(line.replace(/^\d+\.\s+/, '').trim());
  }

  return titleTexts;
}

/**
 * Get body styles of all vehicle cards.
 */
export async function getVehicleBodyStyles(page: Page): Promise<string[]> {
  const results = page.locator('[data-testid="inventory-results"]').last();
  const styles = results.locator('[data-testid="vehicle-body-style"] span');
  const count = await styles.count();
  const bodyStyles: string[] = [];
  for (let i = 0; i < count; i++) {
    const text = await styles.nth(i).textContent();
    if (text) bodyStyles.push(text.toLowerCase());
  }
  if (bodyStyles.length > 0) {
    return bodyStyles;
  }

  const markdownText = await getLastAssistantText(page);
  const matches = markdownText.match(/🚗\s*([a-zA-Z-]+)/g) || [];
  for (const match of matches) {
    const style = match.replace(/🚗\s*/, '').trim().toLowerCase();
    if (style) {
      bodyStyles.push(style);
    }
  }

  return bodyStyles;
}

/**
 * Wait for chat to be ready (initial greeting message visible).
 */
export async function waitForChatReady(page: Page): Promise<void> {
  await expect(page.locator('[data-testid="chat-messages"]')).toBeVisible();
  await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled();
}
