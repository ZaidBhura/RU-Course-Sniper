import { test, expect } from "@playwright/test";

function randomEmail() {
  return `test_${Date.now()}_${Math.random().toString(36).slice(2)}@example.com`;
}

test.describe("Authentication", () => {
  test("shows auth page when unauthenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/auth/);
    await expect(page.getByText("RU")).toBeVisible();
  });

  test("register new user and redirect to dashboard", async ({ page }) => {
    await page.goto("/auth");
    await page.getByRole("button", { name: /register/i }).click();

    const email = randomEmail();
    await page.getByPlaceholder("user@rutgers.edu").fill(email);
    await page.getByPlaceholder("Min. 8 characters").fill("testpassword123");
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText("Dashboard")).toBeVisible();
  });

  test("login with valid credentials", async ({ page }) => {
    await page.goto("/auth");

    const email = randomEmail();
    await page.getByRole("button", { name: /register/i }).click();
    await page.getByPlaceholder("user@rutgers.edu").fill(email);
    await page.getByPlaceholder("Min. 8 characters").fill("testpassword123");
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.getByRole("button", { name: /user menu/i }).click();
    await page.getByText(/sign out/i).click();
    await expect(page).toHaveURL(/\/auth/);

    await page.getByPlaceholder("user@rutgers.edu").fill(email);
    await page.getByPlaceholder("••••••••").fill("testpassword123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("shows error for invalid credentials", async ({ page }) => {
    await page.goto("/auth");
    await page.getByPlaceholder("user@rutgers.edu").fill("wrong@example.com");
    await page.getByPlaceholder("••••••••").fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/invalid|incorrect|password/i)).toBeVisible();
  });

  test("protected route redirects unauthenticated user", async ({ page }) => {
    await page.goto("/dashboard/watchlist");
    await expect(page).toHaveURL(/\/auth/);
  });

  test("authenticated user redirected from /auth to /dashboard", async ({ page, context }) => {
    await page.goto("/auth");
    const email = randomEmail();
    await page.getByRole("button", { name: /register/i }).click();
    await page.getByPlaceholder("user@rutgers.edu").fill(email);
    await page.getByPlaceholder("Min. 8 characters").fill("testpassword123");
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.goto("/auth");
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
