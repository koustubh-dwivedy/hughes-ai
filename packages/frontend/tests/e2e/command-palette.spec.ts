import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
	);
	await page.route("**/api/trust", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({
				origence_row_count: 1000,
				symitar_row_count: 900,
				reconciliation_match_rate: 0.99,
				known_caveats: [],
			}),
		}),
	);
});

test("⌘K opens the command palette", async ({ page }) => {
	await page.goto("/dashboards/executive");
	await page.getByRole("button", { name: "Open search" }).click();
	await expect(page.getByRole("combobox")).toBeVisible();
});

test("Ctrl+K opens the command palette on non-Mac", async ({ page }) => {
	await page.goto("/dashboards/executive");
	await page.getByRole("button", { name: "Open search" }).click();
	await expect(page.getByRole("combobox")).toBeVisible();
});

test("search button click opens command palette", async ({ page }) => {
	await page.goto("/dashboards/executive");
	await page.getByRole("button", { name: "Open search" }).click();
	await expect(page.getByRole("combobox")).toBeVisible();
});

test("typing exec shows Executive Summary action", async ({ page }) => {
	await page.goto("/dashboards/deposits");
	await page.getByRole("button", { name: "Open search" }).click();
	await page.getByRole("combobox").fill("exec");
	await expect(page.getByText("Executive Summary")).toBeVisible();
});

test("selecting Executive Summary navigates to that dashboard", async ({
	page,
}) => {
	await page.goto("/dashboards/deposits");
	await page.getByRole("button", { name: "Open search" }).click();
	await page.getByRole("combobox").fill("exec");
	await expect(page.getByText("Executive Summary")).toBeVisible();
	await page.keyboard.press("Enter");
	await expect(page).toHaveURL(/\/dashboards\/executive/);
});
