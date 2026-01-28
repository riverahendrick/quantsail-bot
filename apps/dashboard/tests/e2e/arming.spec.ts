import { test, expect } from '@playwright/test';

test('ARM LIVE Flow', async ({ page }) => {
  // 1. Go to private overview
  await page.goto('/app/overview');
  
  // Login (mock)
  await page.getByTestId('email-input').fill('admin@quantsail.com');
  await page.getByTestId('password-input').fill('password');
  await page.getByTestId('login-btn').click();
  
  // 2. Open ARM Modal
  await page.getByRole('button', { name: 'ARM LIVE' }).click();
  
  // 3. Step 1: Request Token
  await expect(page.getByText('Step 1: Request arming token')).toBeVisible();
  await page.getByRole('button', { name: 'Request Arming Token' }).click();
  
  // 4. Step 2: Confirm
  await expect(page.getByText('System Armed')).toBeVisible();
  await page.getByRole('button', { name: 'CONFIRM LIVE START' }).click();
  
  // 5. Success
  await expect(page.getByText('LIVE TRADING ACTIVE')).toBeVisible();
});
