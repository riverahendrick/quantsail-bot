import { test, expect } from '@playwright/test';

test.describe('Public Pages Flow', () => {

  test('Public Overview renders sanitised KPIs and chart', async ({ page }) => {
    await page.goto('/public/overview');
    
    // Check Title
    await expect(page.getByRole('heading', { name: 'Public overview' })).toBeVisible();
    
    // Check Status Banner (Sanitized)
    await expect(page.getByText('Status: Running')).toBeVisible();
    
    // Check KPI Cards
    await expect(page.getByText('Equity', { exact: true })).toBeVisible();
    await expect(page.getByText('Realized Today')).toBeVisible();
    
    // Check Chart
    await expect(page.getByRole('heading', { name: 'Equity Curve (Simulated)' })).toBeVisible();
  });

  test('Public Trades renders sanitized table', async ({ page }) => {
    await page.goto('/public/trades');
    
    await expect(page.getByRole('heading', { name: 'Public Trades Feed' })).toBeVisible();
    
    // Verify table headers present
    await expect(page.getByText('Symbol')).toBeVisible();
    await expect(page.getByText('Side')).toBeVisible();
    await expect(page.getByText('PnL')).toBeVisible();
    
    // Verify sanitized content (Mock data logic)
    // Should NOT show internal IDs or secrets
    const content = await page.content();
    expect(content).not.toContain('exchange_order_id');
    expect(content).not.toContain('api_key');
  });

  test('Public Transparency renders explanation', async ({ page }) => {
    await page.goto('/public/transparency');
    
    await expect(page.getByRole('heading', { name: 'Transparency Report' })).toBeVisible();
    
    // Check sections
    await expect(page.getByRole('heading', { name: 'Strategy Pipeline' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Safety Mechanisms' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Data Privacy & Sanitization' })).toBeVisible();
  });

});
