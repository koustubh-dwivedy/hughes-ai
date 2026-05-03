import { expect, test } from "@playwright/test";

const TRUST_RESPONSE = {
	origence_row_count: 500,
	symitar_row_count: 500,
	reconciliation_match_rate: 0.987,
	known_caveats: ["Synthetic data only — no real member data."],
};

test.describe("data sources page", () => {
	test("renders source counts, reconciliation rate, and caveats", async ({
		page,
	}) => {
		await page.route("**/api/trust", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(TRUST_RESPONSE),
			}),
		);
		await page.route("**/api/dashboards/available-months**", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ months: [] }),
			}),
		);

		await page.goto("/data/sources");

		await expect(
			page.getByRole("heading", { name: "Sources & Freshness" }),
		).toBeVisible();
		await expect(page.getByText(/Origence/i).first()).toBeVisible();
		await expect(page.getByText(/Symitar/i).first()).toBeVisible();
		await expect(page.getByText("98.7%")).toBeVisible();
		await expect(
			page.getByText("Synthetic data only — no real member data."),
		).toBeVisible();
	});
});
