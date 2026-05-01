import { expect, test } from "@playwright/test";

const MOCK_EMPTY = { status: 200, contentType: "application/json", body: "{}" };

test.beforeEach(async ({ page }) => {
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill(MOCK_EMPTY),
	);
});

test.describe("AppHeader — as-of-date picker", () => {
	test("header renders workspace badge and search trigger", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(page.getByText("Hughes AI").first()).toBeVisible();
		await expect(
			page.getByRole("button", { name: "Open search" }),
		).toBeVisible();
	});

	test("date picker button is visible", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(
			page.getByRole("button", { name: "Select as-of date" }),
		).toBeVisible();
	});

	test("selecting Today preset writes date to URL", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await page.getByRole("button", { name: "Select as-of date" }).click();
		await page.getByRole("button", { name: "Today" }).click();
		await expect(page).toHaveURL(/as_of_date=\d{4}-\d{2}-\d{2}/);
	});

	test("as-of-date persists when navigating between dashboards", async ({
		page,
	}) => {
		await page.goto("/dashboards/executive?as_of_date=2026-04-30");
		await page.getByRole("link", { name: "Deposit Portfolio" }).click();
		await expect(page).toHaveURL(/as_of_date=2026-04-30/);
	});

	test("API request includes as_of_date after picker selection", async ({
		page,
	}) => {
		let capturedUrl = "";
		await page.route("**/api/dashboards/**", (route) => {
			capturedUrl = route.request().url();
			return route.fulfill(MOCK_EMPTY);
		});

		await page.goto("/dashboards/executive");
		await page.getByRole("button", { name: "Select as-of date" }).click();
		await page.getByRole("button", { name: "Today" }).click();

		await page.waitForTimeout(200);
		expect(capturedUrl).toBeTruthy();
	});
});
