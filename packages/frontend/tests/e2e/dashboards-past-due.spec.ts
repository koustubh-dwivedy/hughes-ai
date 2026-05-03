import { expect, test } from "@playwright/test";

const FIXTURE = {
	data: {
		past_due_total: 1_030_000,
		past_due_total_delta: 30_000,
		nonaccrual_total: 200_000,
		nonaccrual_total_delta: 10_000,
		watchlist_count: 25,
		watchlist_count_delta: 2,
		nonperforming_balance: 150_000,
		nonperforming_balance_delta: 5_000,
		past_due_by_officer: [
			{ officer_name: "J. Smith", balance: 515_000, count: 13 },
		],
		delinquency_trend_13_months: [
			{
				month: "2024-12",
				bucket_30_59: 300_000,
				bucket_60_89: 150_000,
				bucket_90_plus: 80_000,
			},
		],
		past_due_ratio_trend: [{ month: "2024-12", ratio: 0.024 }],
	},
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test-past-due",
};

test("Past Due renders KPI tiles without error", async ({ page }) => {
	await page.route("**/api/dashboards/past-due**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(FIXTURE),
		}),
	);

	await page.goto("/dashboards/past-due");

	await expect(
		page.getByRole("heading", { name: "Past Due", exact: true }),
	).toBeVisible();

	for (const label of [
		"Past Due Total",
		"Loans Earning No Interest",
		"Loans Under Watch",
		"Non-Performing Balance",
	]) {
		await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
	}

	await expect(page.locator('[role="alert"]')).not.toBeVisible();
});
