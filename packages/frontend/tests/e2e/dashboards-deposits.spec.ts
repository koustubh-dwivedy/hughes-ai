import { expect, test } from "@playwright/test";

const TOP_DEPOSITORS = Array.from({ length: 25 }, (_, i) => ({
	member_name: `Member ${i + 1}`,
	balance: 1_000_000 - i * 10_000,
	share_pct: (2.8 - i * 0.05),
}));

const FIXTURE = {
	data: {
		total_deposits: 35_200_000,
		mtd_change: 800_000,
		ytd_change: 3_100_000,
		avg_balance_per_customer: 5_000,
		account_count: 7_040,
		top_25_deposits: TOP_DEPOSITORS,
		deposits_by_branch: [
			{ branch_name: "Main", balance: 20_000_000 },
			{ branch_name: "North", balance: 10_000_000 },
			{ branch_name: "South", balance: 5_200_000 },
		],
		deposit_mix: [
			{ product: "Checking", balance: 15_000_000, share_pct: 42.6 },
			{ product: "Savings", balance: 12_000_000, share_pct: 34.1 },
			{ product: "CD", balance: 8_200_000, share_pct: 23.3 },
		],
		change_by_product: [
			{ product: "Checking", delta: 400_000 },
			{ product: "Savings", delta: 300_000 },
			{ product: "CD", delta: 100_000 },
		],
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
		// exact: insight bullets / chart subtitles include lowercase
		// substrings ("...of total deposits") that would otherwise match.
		await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
	}

	await expect(page.locator('[role="alert"]')).not.toBeVisible();
});

test("Deposit Portfolio shows numeric KPI values (not zero/empty)", async ({
	page,
}) => {
	await page.route("**/api/dashboards/deposit-portfolio**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(FIXTURE),
		}),
	);
	await page.goto("/dashboards/deposits");
	// Total Deposits = $35.2M (formatted via fmt)
	await expect(page.getByText("$35.2M").first()).toBeVisible();
});

test("Deposit Portfolio top-25 table renders 25 rows", async ({ page }) => {
	await page.route("**/api/dashboards/deposit-portfolio**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(FIXTURE),
		}),
	);
	await page.goto("/dashboards/deposits");
	const table = page.getByRole("table").last();
	await expect(table).toBeVisible();
	// 25 data rows + 1 header row
	await expect(table.locator("tbody tr")).toHaveCount(25);
});
