/**
 * URL ↔ store ↔ API ↔ rendered date round-trip.
 *
 * Every checkpoint asserts the same date appears in all four places:
 *   - URL: ?as_of_date=YYYY-MM-DD
 *   - Store: read by the per-dashboard MonthSelector via useDashboardContext
 *   - API: every /api/dashboards/* fetch carries as_of_date=... in its query
 *   - Rendered: the MonthSelector <select> shows the matching month value
 *
 * Replaces the older global DatePicker (now removed) with the per-surface
 * Month dropdown that pulls available months from /dashboards/available-months.
 */

import { expect, test } from "@playwright/test";

const ENVELOPE = JSON.stringify({
	data: null,
	as_of_date: "2026-04-30",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "url-state",
});

const AVAILABLE_MONTHS = [
	"2026-04-01",
	"2026-03-15",
	"2026-03-01",
	"2026-02-01",
];

async function setup(page: import("@playwright/test").Page) {
	const seenUrls: string[] = [];
	// Register the broad handler first so the more-specific
	// available-months handler (registered after) takes precedence —
	// Playwright runs the most-recently-added matching handler.
	await page.route("**/api/dashboards/**", (route, request) => {
		const u = request.url();
		seenUrls.push(u);
		return route.fulfill({
			status: 200,
			contentType: "application/json",
			body: ENVELOPE,
		});
	});
	await page.route("**/api/dashboards/available-months**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ months: AVAILABLE_MONTHS }),
		}),
	);
	await page.route("**/api/trust**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({
				origence_row_count: 1,
				symitar_row_count: 1,
				reconciliation_match_rate: 1,
				known_caveats: [],
			}),
		}),
	);
	await page.route("**/api/history**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
	);
	return { seenUrls };
}

function urlsContaining(urls: string[], substr: string): string[] {
	return urls.filter((u) => u.includes(substr));
}

test.describe("URL state ↔ store ↔ API ↔ rendered date", () => {
	test("loading with ?as_of_date=YYYY-MM-DD propagates everywhere", async ({
		page,
	}) => {
		const { seenUrls } = await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-03-15");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();
		await expect(page).toHaveURL(/as_of_date=2026-03-15/);
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-03-15");
		expect(
			urlsContaining(seenUrls, "as_of_date=2026-03-15").length,
		).toBeGreaterThan(0);
	});

	test("changing the month via dropdown updates URL + API + selector", async ({
		page,
	}) => {
		const { seenUrls } = await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-04-01");
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-04-01");

		await page.getByLabel("As-of month").selectOption("2026-02-01");
		await expect(page).toHaveURL(/as_of_date=2026-02-01/);
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-02-01");
		expect(
			urlsContaining(seenUrls, "as_of_date=2026-02-01").length,
		).toBeGreaterThan(0);
	});

	test("date survives navigation between dashboards", async ({ page }) => {
		await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-02-01");
		await expect(page).toHaveURL(/as_of_date=2026-02-01/);

		await page.getByRole("link", { name: "Past Due" }).click();
		await expect(page).toHaveURL(/dashboards\/past-due\?as_of_date=2026-02-01/);
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-02-01");
	});

	test("browser back/forward preserves the date in URL + selector", async ({
		page,
	}) => {
		await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-03-01");
		await page.getByRole("link", { name: "Past Due" }).click();
		await expect(page).toHaveURL(/dashboards\/past-due/);

		await page.goBack();
		await expect(page).toHaveURL(/dashboards\/deposits\?as_of_date=2026-03-01/);
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-03-01");
	});

	test("full page reload re-hydrates from URL", async ({ page }) => {
		await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-04-01");
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-04-01");

		await page.reload();
		await expect(page).toHaveURL(/as_of_date=2026-04-01/);
		await expect(page.getByLabel("As-of month")).toHaveValue("2026-04-01");
	});
});
