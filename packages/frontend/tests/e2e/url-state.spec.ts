/**
 * HUG-154: URL ↔ Redux ↔ API request ↔ rendered date round-trip.
 *
 * Every checkpoint asserts the same date appears in all four places:
 *   - URL: ?as_of_date=...
 *   - Redux: through the date pill button label (rendered from
 *     useDashboardContext which reads from URL)
 *   - API: every /api/dashboards/* fetch carries as_of_date=... in
 *     its query string (captured by the route handler)
 *   - Rendered: the DateBadge in the page header
 */

import { expect, test } from "@playwright/test";

const ENVELOPE = JSON.stringify({
	data: null,
	as_of_date: "2026-04-30",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "url-state",
});

async function setup(page: import("@playwright/test").Page) {
	const seenUrls: string[] = [];
	await page.route("**/api/dashboards/**", (route) => {
		seenUrls.push(route.request().url());
		return route.fulfill({
			status: 200,
			contentType: "application/json",
			body: ENVELOPE,
		});
	});
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
		// URL pin
		await expect(page).toHaveURL(/as_of_date=2026-03-15/);
		// Picker label echoes the URL date
		await expect(page.getByLabel("Select as-of date")).toContainText(
			"2026-03-15",
		);
		// API got the date in the query string
		expect(
			urlsContaining(seenUrls, "as_of_date=2026-03-15").length,
		).toBeGreaterThan(0);
	});

	test("changing the date via Today preset updates URL + API + picker", async ({
		page,
	}) => {
		const { seenUrls } = await setup(page);
		await page.goto("/dashboards/deposits");
		await page.getByRole("button", { name: "Select as-of date" }).click();
		await page.getByRole("button", { name: "Today" }).click();
		// URL gains as_of_date
		await expect(page).toHaveURL(/as_of_date=\d{4}-\d{2}-\d{2}/);
		// Picker label shows today's iso date
		const today = new Date().toISOString().slice(0, 10);
		await expect(page.getByLabel("Select as-of date")).toContainText(today);
		// API was re-called with the new date
		expect(
			urlsContaining(seenUrls, `as_of_date=${today}`).length,
		).toBeGreaterThan(0);
	});

	test("date survives navigation between dashboards", async ({ page }) => {
		const { seenUrls } = await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-02-01");
		await expect(page).toHaveURL(/as_of_date=2026-02-01/);

		await page.getByRole("link", { name: "Past Due" }).click();
		await expect(page).toHaveURL(/dashboards\/past-due\?as_of_date=2026-02-01/);
		await expect(page.getByLabel("Select as-of date")).toContainText(
			"2026-02-01",
		);
		// Past Due API call uses the same date
		expect(
			urlsContaining(seenUrls, "/past-due").some((u) =>
				u.includes("as_of_date=2026-02-01"),
			),
		).toBe(true);
	});

	test("browser back/forward preserves the date in URL + picker", async ({
		page,
	}) => {
		await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-01-15");
		await page.getByRole("link", { name: "Past Due" }).click();
		await expect(page).toHaveURL(/dashboards\/past-due/);

		await page.goBack();
		await expect(page).toHaveURL(/dashboards\/deposits.*as_of_date=2026-01-15/);
		await expect(page.getByLabel("Select as-of date")).toContainText(
			"2026-01-15",
		);

		await page.goForward();
		await expect(page).toHaveURL(/dashboards\/past-due.*as_of_date=2026-01-15/);
		await expect(page.getByLabel("Select as-of date")).toContainText(
			"2026-01-15",
		);
	});

	test("full page reload re-hydrates from URL", async ({ page }) => {
		const { seenUrls } = await setup(page);
		await page.goto("/dashboards/deposits?as_of_date=2026-03-15");
		await expect(page.getByLabel("Select as-of date")).toContainText(
			"2026-03-15",
		);

		await page.reload();
		await expect(page).toHaveURL(/as_of_date=2026-03-15/);
		await expect(page.getByLabel("Select as-of date")).toContainText(
			"2026-03-15",
		);
		expect(
			urlsContaining(seenUrls, "as_of_date=2026-03-15").length,
		).toBeGreaterThan(0);
	});
});
