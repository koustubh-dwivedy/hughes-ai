import { expect, test } from "@playwright/test";

const FIXTURE = {
	data: {
		total_deposits: 35_200_000,
		mtd_change: 800_000,
		ytd_change: 3_100_000,
		avg_balance_per_customer: 5_000,
		account_count: 7_040,
		top_25_deposits: [
			{ member_name: "Member 1", balance: 1_000_000, share_pct: 2.8 },
		],
		deposits_by_branch: [{ branch_name: "Main", balance: 35_200_000 }],
		deposit_mix: [
			{ product: "Checking", balance: 15_000_000, share_pct: 42.6 },
		],
		change_by_product: [{ product: "Checking", delta: 400_000 }],
		new_vs_closed_accounts: {
			opened: { count: 42, amount: 210_000 },
			closed: { count: 18, amount: 90_000 },
		},
	},
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test-deposits",
};

test("Deposit Portfolio renders KPI tiles without error", async ({ page }) => {
	await page.route("**/api/dashboards/deposit-portfolio**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(FIXTURE),
		}),
	);

	await page.goto("/dashboards/deposits");

	await expect(
		page.getByRole("heading", { name: "Deposit Portfolio" }),
	).toBeVisible();

	for (const label of [
		"Total Deposits",
		"MTD Change",
		"YTD Change",
		"Account Count",
		"Avg Balance",
	]) {
		await expect(page.getByText(label)).toBeVisible();
	}

	await expect(page.locator('[role="alert"]')).not.toBeVisible();
});
