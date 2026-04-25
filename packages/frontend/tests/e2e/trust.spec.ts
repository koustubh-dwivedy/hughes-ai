import { expect, test } from "@playwright/test";

const TRUST_RESPONSE = {
	origence_row_count: 500,
	symitar_row_count: 500,
	reconciliation_match_rate: 0.987,
	known_caveats: ["Synthetic data only — no real member data."],
};

test.describe("trust panel", () => {
	test("renders data freshness stats and caveats", async ({ page }) => {
		await page.route("**/api/**", async (route) => {
			const url = new URL(route.request().url());
			const p = url.pathname;
			const method = route.request().method();

			if (p === "/api/trust" && method === "GET") {
				await route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify(TRUST_RESPONSE),
				});
			} else if (p === "/api/history" && method === "GET") {
				// Empty list suppresses HistoryPanel's <aside> to avoid selector ambiguity
				await route.fulfill({
					status: 200,
					contentType: "application/json",
					body: "[]",
				});
			} else {
				await route.continue();
			}
		});

		await page.goto("/");

		const trustPanel = page.locator("aside").filter({ hasText: "Data Freshness" });
		await expect(trustPanel).toBeVisible();

		await expect(trustPanel.getByText("Origence records: 500")).toBeVisible();
		await expect(trustPanel.getByText("Symitar records: 500")).toBeVisible();
		await expect(
			trustPanel.getByText("Reconciliation match rate: 98.7%"),
		).toBeVisible();

		// Caveats disclosure present
		await expect(
			trustPanel.locator("details summary", { hasText: "Known caveats (1)" }),
		).toBeVisible();
	});
});
