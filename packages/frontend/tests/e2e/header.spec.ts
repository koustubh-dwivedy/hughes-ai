import { expect, test } from "@playwright/test";

const MOCK_EMPTY = { status: 200, contentType: "application/json", body: "{}" };

test.beforeEach(async ({ page }) => {
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill(MOCK_EMPTY),
	);
});

test.describe("AppHeader", () => {
	test("renders the workspace name and search trigger", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(
			page.getByText("Cascade Federal Credit Union"),
		).toBeVisible();
		await expect(
			page.getByRole("button", { name: "Open search" }),
		).toBeVisible();
	});

	test("does not render a global as-of-date picker", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(
			page.getByRole("button", { name: "Select as-of date" }),
		).toHaveCount(0);
	});

	test("does not render a user menu button", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(
			page.getByRole("button", { name: "User menu" }),
		).toHaveCount(0);
	});
});
