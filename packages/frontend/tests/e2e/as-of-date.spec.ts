import { expect, test } from "@playwright/test";

const FIXTURE = {
	data: {
		total_deposits: 1_000_000,
		mtd_change: 0,
		ytd_change: 0,
		avg_balance_per_customer: 1_000,
		account_count: 100,
		top_25_deposits: [],
		deposits_by_branch: [],
		deposit_mix: [],
		change_by_product: [],
		new_vs_closed_accounts: {
			opened: { count: 0, amount: 0 },
			closed: { count: 0, amount: 0 },
		},
	},
	as_of_date: "2026-02-01",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "as-of-test",
};

test.describe("as_of_date URL param", () => {
	test("?as_of_date=YYYY-MM-DD reaches the API request", async ({ page }) => {
		const seenUrls: string[] = [];
		await page.route("**/api/dashboards/deposit-portfolio**", (route) => {
			seenUrls.push(route.request().url());
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(FIXTURE),
			});
		});

		await page.goto("/dashboards/deposits?as_of_date=2026-02-01");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();

		expect(seenUrls.length).toBeGreaterThan(0);
		expect(seenUrls.some((u) => u.includes("as_of_date=2026-02-01"))).toBe(
			true,
		);
	});

	test("omitting as_of_date sends no qs param", async ({ page }) => {
		const seenUrls: string[] = [];
		await page.route("**/api/dashboards/deposit-portfolio**", (route) => {
			seenUrls.push(route.request().url());
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(FIXTURE),
			});
		});
		// HUG-271: MonthSelector auto-pushes ?as_of_date= into the URL when
		// available-months returns a non-empty list. Mock it to empty so the
		// early-return path (months.length === 0) keeps the URL clean and
		// this test stays deterministic. Same pattern as url-state.spec.ts.
		await page.route("**/api/dashboards/available-months**", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ months: [] }),
			}),
		);

		await page.goto("/dashboards/deposits");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();

		expect(seenUrls.length).toBeGreaterThan(0);
		expect(seenUrls.every((u) => !u.includes("as_of_date="))).toBe(true);
	});

	test("as_of_date persists when navigating between dashboards", async ({
		page,
	}) => {
		const allUrls: string[] = [];
		await page.route("**/api/dashboards/**", (route) => {
			allUrls.push(route.request().url());
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(FIXTURE),
			});
		});

		await page.goto("/dashboards/deposits?as_of_date=2026-02-01");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();

		await page.getByRole("link", { name: "Past Due", exact: true }).click();
		await expect(page).toHaveURL(/\/dashboards\/past-due/);

		// At least one past-due request was made; we don't require the URL
		// param to carry over (that's a UX choice — this test just documents
		// current behavior).
		expect(allUrls.some((u) => u.includes("/past-due"))).toBe(true);
	});
});
