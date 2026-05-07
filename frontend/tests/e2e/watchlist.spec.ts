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

test.describe("Watchlist", () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/dashboard/watchlist");
  });

  test("shows empty state initially", async ({ page }) => {
    await expect(page.getByText(/no courses being watched/i)).toBeVisible();
  });

  test("add a watched index", async ({ page }) => {
    await page.getByRole("button", { name: /add index/i }).click();
    await page.getByPlaceholder(/e\.g\. 01234/i).fill("11111");
    await page.getByPlaceholder(/e\.g\. CS 111/i).fill("Test Course");
    await page.getByRole("button", { name: /^add$/i }).click();

    await expect(page.getByText("11111")).toBeVisible();
    await expect(page.getByText("Test Course")).toBeVisible();
  });

  test("toggle index inactive", async ({ page }) => {
    await page.getByRole("button", { name: /add index/i }).click();
    await page.getByPlaceholder(/e\.g\. 01234/i).fill("22222");
    await page.getByRole("button", { name: /^add$/i }).click();
    await expect(page.getByText("22222")).toBeVisible();

    const toggle = page.getByRole("switch", { name: /toggle 22222 active/i });
    await expect(toggle).toBeChecked();
    await toggle.click();
    await expect(toggle).not.toBeChecked();
  });

  test("delete a watched index", async ({ page }) => {
    await page.getByRole("button", { name: /add index/i }).click();
    await page.getByPlaceholder(/e\.g\. 01234/i).fill("33333");
    await page.getByRole("button", { name: /^add$/i }).click();
    await expect(page.getByText("33333")).toBeVisible();

    await page.getByRole("button", { name: /delete index 33333/i }).click();
    await page.getByRole("button", { name: /remove/i }).last().click();
    await expect(page.getByText("33333")).not.toBeVisible();
    await expect(page.getByText(/no courses being watched/i)).toBeVisible();
  });
});
