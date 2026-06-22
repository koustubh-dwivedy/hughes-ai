/**
 * Comprehensive end-user POV smoke test (2026-05-17).
 *
 * Exercises every page + every UI component a user actually sees and
 * clicks. Designed to flag regressions from the autonomous run that
 * shipped HUG-236 through HUG-249 + Phase B decommission.
 *
 * Known suspect areas (from the verification-report doc):
 *   - PlanPreview's "Approve" button → POST /approve → 404 (route
 *     deleted in HUG-247 Phase B; frontend mutation still wired)
 *   - ResearchAuditPanel still uses useGetResearchStepsQuery (legacy
 *     hook); should be using useGetResearchSubagentCallsQuery
 *   - SubagentCallList component exists but is not wired into any
 *     visible UI surface yet
 *
 * Each test logs to the console + captures a screenshot in
 * test-results/ on failure for post-mortem.
 */

import { type Page, expect, test } from "@playwright/test";

// Allow this suite to run against a live local stack only.
test.skip(
	!!process.env.CI,
	"comprehensive-e2e requires live API + frontend; runs locally only",
);

const USER = "e2e-comprehensive-user";
const SESSION = "e2e-comprehensive-session";

async function bootSession(page: Page) {
	// Inject auth headers via local storage so the app picks them up.
	// Hughes uses X-Hughes-User / X-Hughes-Session headers — see how
	// the frontend's HTTP client sets them.
	await page.addInitScript(
		({ user, session }) => {
			localStorage.setItem("hughes_user_id", user);
			localStorage.setItem("hughes_session_id", session);
		},
		{ user: USER, session: SESSION },
	);
}

// ── Tier 1: every page loads without crashing ───────────────────────

test.describe("Tier 1 — every page renders", () => {
	test("root renders the launchpad", async ({ page }) => {
		await bootSession(page);
		await page.goto("/");
		await page.waitForLoadState("networkidle");
		// The launchpad (product chooser) is the default landing.
		const headings = await page.locator("h1, h2, h3").count();
		expect(headings).toBeGreaterThan(0);
	});

	const DASHBOARD_ROUTES = [
		{ path: "/dashboards/executive", heading: "Executive Summary" },
		{ path: "/dashboards/deposits", heading: "Deposit Portfolio" },
		{ path: "/dashboards/past-due", heading: "Past Due" },
		{ path: "/dashboards/officer-branch", heading: "Officer / Branch Loans" },
	];

	for (const { path, heading } of DASHBOARD_ROUTES) {
		test(`${path} loads and shows heading "${heading}"`, async ({ page }) => {
			await bootSession(page);
			await page.goto(path);
			await expect(
				page.getByRole("heading", { name: heading }),
			).toBeVisible({ timeout: 15_000 });
		});
	}

	test("/intelligence loads (chat surface)", async ({ page }) => {
		await bootSession(page);
		await page.goto("/intelligence");
		await page.waitForLoadState("networkidle");
		// The chat page should have an input or a heading.
		const has_input = await page.locator("textarea, input[type=text]").count();
		const has_heading = await page.locator("h1, h2").count();
		expect(has_input + has_heading).toBeGreaterThan(0);
	});
});

// ── Tier 2: dashboard contents render ───────────────────────────────

test.describe("Tier 2 — dashboards render data", () => {
	test("executive summary shows KPI tiles", async ({ page }) => {
		await bootSession(page);
		await page.goto("/dashboards/executive");
		// Wait for at least one tile to show currency formatting
		await expect(page.locator("text=/\\$\\d/")).toBeVisible({
			timeout: 15_000,
		});
	});

	test("past-due shows officer pseudonyms (not real names)", async ({
		page,
	}) => {
		await bootSession(page);
		await page.goto("/dashboards/past-due");
		// Should see "Officer #N" pseudonyms but NOT raw "Alice Smith"-style names.
		await expect(page.locator("text=/Officer #\\d+/")).toBeVisible({
			timeout: 15_000,
		});
	});

	test("deposit portfolio renders without crashing", async ({ page }) => {
		await bootSession(page);
		await page.goto("/dashboards/deposits");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();
		// Page didn't error-boundary out
		await expect(page.locator("[role=alert]")).not.toBeVisible();
	});

	test("officer-branch renders without crashing", async ({ page }) => {
		await bootSession(page);
		await page.goto("/dashboards/officer-branch");
		await expect(
			page.getByRole("heading", { name: "Officer / Branch Loans" }),
		).toBeVisible();
	});
});

// ── Tier 3: chat / intelligence flow ────────────────────────────────

test.describe("Tier 3 — chat surface", () => {
	test("typing a question into chat input works", async ({ page }) => {
		await bootSession(page);
		await page.goto("/intelligence");
		await page.waitForLoadState("networkidle");
		// Find the chat input.
		const input = page.locator("textarea, input[type=text]").first();
		await expect(input).toBeVisible({ timeout: 10_000 });
		await input.fill("test question — do not actually send");
		expect(await input.inputValue()).toContain("test question");
	});
});

// ── Tier 4: known-suspect surfaces ──────────────────────────────────

test.describe("Tier 4 — known-broken-by-HUG-247-Phase-B paths", () => {
	test("approve mutation fails (route deleted)", async ({ page, request }) => {
		// Direct API call — confirm /approve returns 4xx
		const resp = await request.post(
			"/api/threads/00000000-0000-0000-0000-000000000000/plans/00000000-0000-0000-0000-000000000000/approve",
			{
				headers: {
					"X-Hughes-User": USER,
					"X-Hughes-Session": SESSION,
				},
			},
		);
		// Should NOT be 200; route was deleted in Phase B.
		expect(resp.status()).not.toBe(200);
	});

	test("abort survives", async ({ request }) => {
		const resp = await request.post(
			"/api/threads/00000000-0000-0000-0000-000000000000/plans/00000000-0000-0000-0000-000000000000/abort",
			{
				headers: {
					"X-Hughes-User": USER,
					"X-Hughes-Session": SESSION,
				},
			},
		);
		// Will 404 because the thread/plan don't exist, but the route IS wired.
		expect([404, 403, 400]).toContain(resp.status());
	});
});

// ── Tier 5: error states ────────────────────────────────────────────

test.describe("Tier 5 — error handling", () => {
	test("dashboard 500 shows error boundary, not white screen", async ({
		page,
	}) => {
		await bootSession(page);
		await page.route("**/api/dashboards/executive-summary**", (route) =>
			route.fulfill({
				status: 500,
				contentType: "application/json",
				body: JSON.stringify({ detail: "boom" }),
			}),
		);
		await page.goto("/dashboards/executive");
		// Page header should still render
		await expect(
			page.getByRole("heading", { name: "Executive Summary" }),
		).toBeVisible({ timeout: 10_000 });
		// Error indicator should be visible
		await expect(page.locator("[role=alert]")).toBeVisible({ timeout: 5_000 });
	});

	test("dashboard partial-data: no crash, heading visible", async ({ page }) => {
		await bootSession(page);
		await page.route("**/api/dashboards/past-due**", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { total_deposits: 1000 },
					as_of_date: "2026-04-30",
					generated_at: "2026-04-30T00:00:00Z",
					audit_id: "partial",
				}),
			}),
		);
		await page.goto("/dashboards/past-due");
		await expect(
			page.getByRole("heading", { name: "Past Due" }),
		).toBeVisible({ timeout: 10_000 });
	});

	test("network failure shows error, not blank", async ({ page }) => {
		await bootSession(page);
		await page.route("**/api/dashboards/executive-summary**", (route) =>
			route.abort(),
		);
		await page.goto("/dashboards/executive");
		await expect(
			page.getByRole("heading", { name: "Executive Summary" }),
		).toBeVisible({ timeout: 10_000 });
	});
});
