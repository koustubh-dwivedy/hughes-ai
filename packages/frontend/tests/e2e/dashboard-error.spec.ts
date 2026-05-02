import { expect, test } from "@playwright/test";

test.describe("dashboard error states", () => {
	test("HTTP 500 on /past-due renders error UI, not a blank page", async ({
		page,
	}) => {
		await page.route("**/api/dashboards/past-due**", (route) =>
			route.fulfill({
				status: 500,
				contentType: "application/json",
				body: JSON.stringify({ detail: "boom" }),
			}),
		);

		await page.goto("/dashboards/past-due");

		await expect(
			page.getByRole("heading", { name: "Past Due", exact: true }),
		).toBeVisible();

		// Either a role=alert is shown, or some visible "error" copy. We don't
		// require a specific string so the spec stays robust to copy changes.
		// Use toBeVisible() instead of count() so Playwright auto-waits — the
		// older count()-based assertion was racy: it ran before RTK Query
		// finished propagating isError, marked the test as flaky.
		const errIndicator = page
			.locator('[role="alert"]')
			.or(page.getByText(/error|failed|HTTP/i));
		await expect(errIndicator.first()).toBeVisible();
	});

	test("a single dashboard error doesn't break sibling navigation", async ({
		page,
	}) => {
		await page.route("**/api/dashboards/past-due**", (route) =>
			route.fulfill({ status: 500, contentType: "application/json", body: "{}" }),
		);
		// Other dashboards stay healthy
		await page.route("**/api/dashboards/executive-summary**", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: "{}",
			}),
		);

		await page.goto("/dashboards/past-due");
		await expect(
			page.getByRole("heading", { name: "Past Due", exact: true }),
		).toBeVisible();

		await page.getByRole("link", { name: "Executive Summary" }).click();
		await expect(
			page.getByRole("heading", { name: "Executive Summary" }),
		).toBeVisible();
	});

	test("network abort on a dashboard surfaces a non-blank error state", async ({
		page,
	}) => {
		await page.route("**/api/dashboards/deposit-portfolio**", (route) =>
			route.abort(),
		);
		await page.goto("/dashboards/deposits");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();
		// Error visible somewhere on the page
		const errorText = page.getByText(/error|failed|fetch/i);
		expect(await errorText.count()).toBeGreaterThan(0);
	});
});
