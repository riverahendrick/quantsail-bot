import { test, expect } from '@playwright/test';

test('Private Overview Page Flow', async ({ page }) => {
  // 1. Go to private page
  await page.goto('/app/overview');

  // 2. Expect Login
  await expect(page.getByText('Private Dashboard Login')).toBeVisible();

  // 3. Mock Login
  await page.getByTestId('email-input').fill('admin@quantsail.com');
  await page.getByTestId('password-input').fill('password');
  await page.getByTestId('login-btn').click();

  // 4. Expect Dashboard content
  await expect(page.getByRole('heading', { name: 'Operator Dashboard' })).toBeVisible();
  
  // 5. Expect Widgets
  await expect(page.getByRole('heading', { name: 'Daily Target Lock' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Active Breakers' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Recent Trades' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Equity Curve (Simulated)' })).toBeVisible();
  
  // 6. Expect Status Banner (default unknown)
  await expect(page.getByText('Unknown')).toBeVisible();
});
