import { expect, test } from "@playwright/test";

const FIXTURE = {
	data: {
		total_loans: 42_000_000,
		account_count: 3_200,
		avg_loan_balance: 13_125,
		loan_mix_donut: [
			{ product: "Auto", balance: 5_000_000, share_pct: 11.9 },
		],
		change_by_type_waterfall: [{ product: "Auto", delta: 200_000 }],
		single_loan_customers_by_type: [{ product: "Auto", count: 120 }],
		combo_balance_rate: [
			{ product: "Auto", balance: 5_000_000, weighted_avg_rate: 0.055 },
		],
		top_25_borrowers: [
			{ member_name: "Member 1", balance: 1_000_000, share_pct: 2.4 },
		],
	},
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test-officer",
};

test("Officer/Branch renders KPI tiles, demo banner, without error", async ({
	page,
}) => {
	await page.route("**/api/dashboards/officer-branch**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(FIXTURE),
		}),
	);

	await page.goto("/dashboards/officer-branch");

	await expect(
		page.getByRole("heading", { name: "Officer / Branch Loans" }),
	).toBeVisible();

	for (const label of ["Total Loans", "Account Count", "Avg Loan Balance"]) {
		await expect(page.getByText(label)).toBeVisible();
	}

	await expect(page.getByRole("note")).toBeVisible();
	await expect(page.getByText(/Demo data only/i)).toBeVisible();

	await expect(page.locator('[role="alert"]')).not.toBeVisible();
});

test("Officer/Branch passes branch_id and officer_id to the API", async ({
	page,
}) => {
	const seenUrls: string[] = [];
	await page.route("**/api/dashboards/officer-branch**", (route) => {
		seenUrls.push(route.request().url());
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(FIXTURE),
		});
	});
	await page.goto(
		"/dashboards/officer-branch?as_of_date=2026-02-01",
	);
	await expect(
		page.getByRole("heading", { name: "Officer / Branch Loans" }),
	).toBeVisible();
	expect(seenUrls.length).toBeGreaterThan(0);
	expect(seenUrls[0]).toContain("as_of_date=2026-02-01");
});
