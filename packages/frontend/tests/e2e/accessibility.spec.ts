import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ROUTES = [
	"/dashboards/executive",
	"/dashboards/deposits",
	"/dashboards/past-due",
	"/dashboards/officer-branch",
	"/intelligence",
] as const;

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

for (const route of ROUTES) {
	test(`a11y: ${route} has zero serious/critical axe violations`, async ({
		page,
	}) => {
		await page.goto(route);
		// Wait for the steady-state UI: dashboards have an h1, the
		// /intelligence surface only has the AskInput textbox.
		if (route === "/intelligence") {
			await expect(page.getByRole("textbox")).toBeVisible();
		} else {
			await expect(page.locator("h1")).toBeVisible();
		}
		const results = await new AxeBuilder({ page })
			.withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
			// Pre-existing issues tracked separately:
			// - color-contrast: slate[400-500] muted text on white sits just
			//   below AA 4.5:1 (design-system token sweep)
			// - aria-valid-attr-value: Mantine Tabs without <Tabs.Panel>
			//   generates aria-controls pointing at missing IDs (Mantine
			//   library issue, fix: render an empty panel or wait on upstream)
			.disableRules(["color-contrast", "aria-valid-attr-value"])
			.analyze();
		const blocking = results.violations.filter(
			(v) => v.impact === "serious" || v.impact === "critical",
		);
		const summary = blocking.map((v) => ({
			id: v.id,
			impact: v.impact,
			help: v.help,
			nodes: v.nodes.length,
		}));
		expect(summary, `serious/critical a11y violations on ${route}`).toEqual([]);
	});
}
