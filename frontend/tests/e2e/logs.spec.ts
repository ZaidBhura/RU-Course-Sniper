import { test, expect } from "@playwright/test";

function randomEmail() {
  return `test_${Date.now()}_${Math.random().toString(36).slice(2)}@example.com`;
}

async function registerAndLogin(page: import("@playwright/test").Page) {
  await page.goto("/auth");
  await page.getByRole("button", { name: /register/i }).click();
  await page.getByPlaceholder("user@rutgers.edu").fill(randomEmail());
  await page.getByPlaceholder("Min. 8 characters").fill("testpassword123");
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test.describe("Logs", () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/dashboard/logs");
  });

  test("shows empty state for new account", async ({ page }) => {
    await expect(page.getByText(/no notifications yet/i)).toBeVisible();
  });

  test("filter chips are visible", async ({ page }) => {
    await expect(page.getByText("All statuses")).toBeVisible();
    await expect(page.getByText("All channels")).toBeVisible();
    await expect(page.getByText("All events")).toBeVisible();
  });

  test("filter by status updates selection", async ({ page }) => {
    await page.getByRole("button", { name: "Sent" }).click();
    await expect(page.getByRole("button", { name: "Sent" })).toHaveAttribute("aria-pressed", "true");

    await page.getByRole("button", { name: "Clear" }).click();
    await expect(page.getByRole("button", { name: "All statuses" })).toHaveAttribute("aria-pressed", "true");
  });
});
