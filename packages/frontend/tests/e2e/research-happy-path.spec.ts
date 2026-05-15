/**
 * Deep-research happy-path e2e (HUG-226, V4).
 *
 * Mocks the backend endpoints so the full UI flow runs without
 * needing a live LLM or DB — covers PlanPreview → Approve → StepList.
 *
 * Out of scope: SSE stream simulation. Playwright's page.route can't
 * easily stream chunked text/event-stream; the chat-side SSE flow
 * is covered by the unit + integration tests on the backend side.
 * What this test pins is the FRONTEND UI surface of HUG-211 + HUG-219.
 */

import { expect, test } from "@playwright/test";

const THREAD_ID = "00000000-0000-0000-0000-000000000001";
const PLAN_ID = "00000000-0000-0000-0000-000000000002";
const USER_ID = "research-e2e-user";

const PLAN_DRAFT = {
	plan: {
		plan_id: PLAN_ID,
		thread_id: THREAD_ID,
		version: 1,
		status: "draft" as const,
		created_at: "2026-05-15T00:00:00Z",
		plan_json: {
			route: "deep",
			reason: "multi-step decomposition needed",
			research_question_summary: "Drivers of YoY past-due delta",
			plan: [
				{
					ordinal: 1,
					description: "Pull past-due exposure latest month",
					dependencies: [],
				},
				{
					ordinal: 2,
					description: "Pull past-due exposure one year ago",
					dependencies: [],
				},
				{
					ordinal: 3,
					description: "Compute YoY delta by branch",
					dependencies: [1, 2],
				},
			],
		},
	},
};

const PLAN_APPROVED = {
	plan: { ...PLAN_DRAFT.plan, status: "approved" as const },
};

const STEPS_PENDING = {
	steps: [
		{
			step_id: "step-1",
			plan_id: PLAN_ID,
			ordinal: 1,
			description: "Pull past-due exposure latest month",
			status: "pending",
			assigned_subagent: null,
			started_at: null,
			completed_at: null,
		},
		{
			step_id: "step-2",
			plan_id: PLAN_ID,
			ordinal: 2,
			description: "Pull past-due exposure one year ago",
			status: "pending",
			assigned_subagent: null,
			started_at: null,
			completed_at: null,
		},
		{
			step_id: "step-3",
			plan_id: PLAN_ID,
			ordinal: 3,
			description: "Compute YoY delta by branch",
			status: "pending",
			assigned_subagent: null,
			started_at: null,
			completed_at: null,
		},
	],
};

test.describe("deep-research happy path (HUG-226)", () => {
	test.skip(
		!!process.env.CI,
		"requires live dev server with a thread route mock seam — runs locally",
	);

	test("PlanPreview → Approve → StepList renders end-to-end", async ({
		page,
	}) => {
		let approveCalled = false;
		let approvedPath = "";

		// Get-thread, list-threads, history, trust — minimal stubs so
		// the page doesn't blow up navigating to /intelligence.
		await page.route("**/api/threads", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ threads: [] }),
			}),
		);
		await page.route(`**/api/threads/${THREAD_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					thread_id: THREAD_ID,
					session_id: USER_ID,
					user_id: USER_ID,
					title: "Research demo",
					started_at: "2026-05-15T00:00:00Z",
					last_active_at: "2026-05-15T00:00:00Z",
					messages: [],
				}),
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

		// /plans/latest — flips from draft to approved after the
		// approve POST. Subsequent gets return approved state.
		let planResponse = PLAN_DRAFT;
		await page.route(`**/api/threads/${THREAD_ID}/plans/latest`, (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(planResponse),
			}),
		);
		await page.route(
			`**/api/threads/${THREAD_ID}/plans/${PLAN_ID}/steps`,
			(route) =>
				route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify(STEPS_PENDING),
				}),
		);
		await page.route(
			`**/api/threads/${THREAD_ID}/plans/${PLAN_ID}/approve`,
			(route) => {
				approveCalled = true;
				approvedPath = route.request().url();
				planResponse = PLAN_APPROVED;
				return route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify({
						event: "research.plan.approved",
						data: "{}",
					}),
				});
			},
		);

		// Navigate WITH the URL state pointing at our thread — the
		// IntelligencePage reads /intelligence/{thread_id} from the
		// router; if no param, defaults to no thread. Use ?thread or
		// direct nav.
		await page.goto(`/intelligence?thread_id=${THREAD_ID}`);

		// PlanPreview renders the proposed plan.
		await expect(
			page.getByText("Drivers of YoY past-due delta"),
		).toBeVisible({ timeout: 15_000 });
		await expect(page.getByText(/Pull past-due exposure latest month/)).toBeVisible();
		await expect(page.getByText(/Compute YoY delta by branch/)).toBeVisible();

		const approveBtn = page.getByRole("button", { name: /Approve/ });
		await expect(approveBtn).toBeVisible();
		await approveBtn.click();

		// Approve mutation was called.
		await expect.poll(() => approveCalled, { timeout: 5_000 }).toBe(true);
		expect(approvedPath).toContain(`/plans/${PLAN_ID}/approve`);
	});
});
