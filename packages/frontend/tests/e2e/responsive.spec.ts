import { expect, test } from "@playwright/test";

const VIEWPORTS = [
	{ name: "phone", width: 375, height: 812 },
	{ name: "tablet", width: 768, height: 1024 },
	{ name: "desktop", width: 1440, height: 900 },
] as const;

const ROUTES = [
	"/dashboards/executive",
	"/dashboards/deposits",
	"/dashboards/past-due",
	"/dashboards/officer-branch",
] as const;

// Returning `data: null` keeps components in their loading-shell state
// and skips the data helpers (which would crash on `{}`); we still get a
// fully laid-out page with the heading and tile/grid skeleton.
const ENVELOPE = JSON.stringify({
	data: null,
	as_of_date: "2026-04-30",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test",
});

test.beforeEach(async ({ page }) => {
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: ENVELOPE,
		}),
	);
	await page.route("**/api/history**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: "[]",
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
});

for (const viewport of VIEWPORTS) {
	test.describe(`@${viewport.name} (${viewport.width}x${viewport.height})`, () => {
		test.use({ viewport: { width: viewport.width, height: viewport.height } });

		for (const route of ROUTES) {
			test(`${route} fits in viewport without horizontal overflow`, async ({
				page,
			}) => {
				await page.goto(route);
				// Wait for page heading so layout settles
				await expect(page.locator("h1")).toBeVisible();
				const overflow = await page.evaluate(() => ({
					scrollWidth: document.documentElement.scrollWidth,
					clientWidth: document.documentElement.clientWidth,
				}));
				// Allow a 1px sub-pixel rounding tolerance
				expect(overflow.scrollWidth).toBeLessThanOrEqual(
					overflow.clientWidth + 1,
				);
			});
		}
	});
}

test.describe("@phone sidebar shows hamburger and hides desktop nav", () => {
	test.use({ viewport: { width: 375, height: 812 } });

	test("hamburger button is visible at <768px", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(page.getByTestId("hamburger")).toBeVisible();
	});
});

test.describe("@tablet sidebar collapses to icon-only", () => {
	test.use({ viewport: { width: 900, height: 1024 } });

	test("sidebar reports data-collapsed=true at 768-1024px", async ({
		page,
	}) => {
		await page.goto("/dashboards/executive");
		const nav = page.getByRole("navigation", { name: "primary" });
		await expect(nav).toHaveAttribute("data-collapsed", "true");
	});
});

test.describe("@desktop sidebar is full width", () => {
	test.use({ viewport: { width: 1440, height: 900 } });

	test("sidebar reports data-collapsed=false at >=1024px", async ({ page }) => {
		await page.goto("/dashboards/executive");
		const nav = page.getByRole("navigation", { name: "primary" });
		await expect(nav).toHaveAttribute("data-collapsed", "false");
	});
});
