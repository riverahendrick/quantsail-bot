import { test, expect } from '@playwright/test';

test('Users Admin Page Flow', async ({ page }) => {
  await page.goto('/app/users');

  await expect(page.getByText('Private Dashboard Login')).toBeVisible();

  await page.getByTestId('email-input').fill('admin@quantsail.com');
  await page.getByTestId('password-input').fill('password');
  await page.getByTestId('login-btn').click();

  await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Create User' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Existing Users' })).toBeVisible();
});
