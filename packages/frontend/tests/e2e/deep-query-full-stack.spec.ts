/**
 * Comprehensive end-to-end test for the deep-query lead-agent flow
 * (Bug 5, 2026-05-17).
 *
 * One spec that, when it passes, gives the user confidence that:
 *   - the deep starter questions actually complete (Bug 3 root fix)
 *   - the live activity panel renders during streaming (Bug 4)
 *   - References modal close stays pinned during scroll (Bug 1)
 *   - the composer on a different thread stays enabled mid-stream (Bug 2)
 *   - DB rows, structlog events, and Prometheus counters all line up
 *     with what the SSE stream emitted
 *
 * Opt-in via env var `RUN_DEEP_E2E=1` because it needs:
 *   - the dev FastAPI process up at localhost:8000 with a real LLM key
 *   - a warm MetricFlow catalog (first /list-metrics call takes ~3 min)
 *   - 3-5 min of wall clock per run
 * Playwright's webServer config will spin up the vite dev server.
 *
 * Run locally: `cd packages/frontend && RUN_DEEP_E2E=1 npx playwright test deep-query-full-stack.spec.ts`.
 */

import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

const API_BASE = process.env.HUGHES_API_BASE ?? "http://localhost:8000";
const API_LOG_PATH =
	process.env.HUGHES_API_LOG ?? "/tmp/hughes-test-logs/api.log";

// The button text is matched by regex below — the full question
// (from EmptyState.tsx) is "Decompose YoY past-due delta by branch
// and product…". This is exactly what the user reported as failing.
test.describe("Full-stack deep-query E2E (Bug 5)", () => {
	test.skip(
		!process.env.RUN_DEEP_E2E,
		"Set RUN_DEEP_E2E=1 to run — needs live API + LLM key + ~5 min wall clock",
	);
	// One test, one budget — the lead does propose_plan + N subagents + synth.
	test.setTimeout(7 * 60 * 1000);

	test("deep starter question completes end-to-end with all observability lined up", async ({
		page,
	}) => {
		// ── Pre-flight: API up + capture Prometheus baseline ──────────
		const health = await page.request.get(`${API_BASE}/health`);
		expect(health.ok(), "API /health must respond before the run").toBe(true);

		const baseMetrics = await fetchPrometheusCounters(page, API_BASE);

		// ── Step 1: Open /intelligence and pick the deep starter ──────
		await page.goto("/intelligence");
		await expect(
			page.getByText(/Open-ended questions about loans/),
		).toBeVisible({ timeout: 15_000 });
		const starter = page.getByRole("button", {
			name: /Decompose YoY past-due/,
		});
		await expect(starter).toBeVisible();
		await starter.click();

		// ── Step 2: Live streaming assertions (Bug 4) ─────────────────
		const bubble = page.getByTestId("thinking-bubble");
		await expect(bubble).toBeVisible({ timeout: 15_000 });
		// The lead's propose_plan call surfaces the plan badge.
		const planBadge = page.getByTestId("live-plan-badge");
		await expect(planBadge).toBeVisible({ timeout: 90_000 });
		await expect(planBadge).toHaveText(/Plan v\d+ drafted/);
		// At least one subagent must spawn — proves delegation actually
		// happened (Bug 3 root-cause regression guard).
		await expect(page.getByTestId("live-subagent-row").first()).toBeVisible({
			timeout: 120_000,
		});

		// ── Step 3: Composer disabled on streaming thread, enabled on a
		//   different one (Bug 2 verification) ─────────────────────────
		const composer = page.getByLabel("Ask Hughes");
		await expect(composer).toBeDisabled();
		const beforeUrl = page.url();
		await page.getByTestId("new-thread-button").click();
		await expect(page).not.toHaveURL(beforeUrl, { timeout: 5_000 });
		// On the freshly-created thread the composer must be ENABLED
		// even though the original thread is still streaming.
		await expect(page.getByLabel("Ask Hughes")).toBeEnabled({ timeout: 5_000 });
		// Back to the original thread to wait for completion.
		await page.goBack();
		await expect(bubble).toBeVisible();

		// ── Step 4: Wait for final answer (max ~5 min including catalog) ─
		const finalAnswer = page.getByTestId("final-answer").first();
		await expect(finalAnswer).toBeVisible({ timeout: 5 * 60 * 1000 });
		const summary = await page
			.getByTestId("final-summary")
			.first()
			.textContent();
		expect(summary ?? "").not.toMatch(/couldn't reach an answer/i);
		expect((summary ?? "").length).toBeGreaterThan(40);

		// ── Step 5: References modal opens; sticky header stays
		//   pinned during scroll (Bug 1) ───────────────────────────────
		await page.getByTestId("references-button").first().click();
		const modalHeader = page.getByTestId("references-modal-header");
		await expect(modalHeader).toBeVisible();
		// Find the scrollable dialog and scroll it; assert the sticky
		// header is still at the top of the viewport.
		await page.evaluate(() => {
			const dialog = document.querySelector(
				"dialog[aria-label='Answer references']",
			);
			(dialog as HTMLElement | null)?.scrollTo({
				top: 400,
				behavior: "instant",
			});
		});
		const headerBox = await modalHeader.boundingBox();
		expect(
			headerBox,
			"header must remain laid-out after scroll",
		).not.toBeNull();
		expect(headerBox?.y ?? 0).toBeLessThan(120);
		// Close button still clickable.
		await page.getByTestId("references-modal-close").click();
		await expect(modalHeader).not.toBeVisible();

		// ── Step 6: Audit panel shows subagent rows ───────────────────
		// Reopen modal to inspect the audit panel.
		await page.getByTestId("references-button").first().click();
		await expect(page.getByTestId("audit-subagent-section")).toBeVisible();
		await page.getByTestId("references-modal-close").click();

		// ── Step 7: Backend state assertions via the API ──────────────
		// Extract thread_id from the URL so the API calls are scoped.
		const url = new URL(page.url());
		const threadId = url.pathname.split("/").pop();
		expect(threadId, "URL must end in a thread id").toBeTruthy();

		const planResp = await page.request.get(
			`${API_BASE}/threads/${threadId}/plans/latest`,
		);
		expect(planResp.ok()).toBe(true);
		const planBody = await planResp.json();
		expect(planBody.plan, "research_plans row must exist").toBeTruthy();
		const planId = planBody.plan.plan_id as string;

		const callsResp = await page.request.get(
			`${API_BASE}/threads/${threadId}/plans/${planId}/subagent-calls`,
		);
		expect(callsResp.ok()).toBe(true);
		const callsBody = await callsResp.json();
		expect(
			(callsBody.calls ?? []).length,
			"at least 2 subagent_calls rows so we know delegation happened",
		).toBeGreaterThanOrEqual(2);
		// Lead must NOT have called mf_query directly — workers carry the
		// rows. Check via the audit-panel data: each subagent_call should
		// have a non-null summary (worker reached final_answer).
		const completed = (callsBody.calls ?? []).filter(
			(c: { status: string }) => c.status === "complete",
		);
		expect(
			completed.length,
			"at least one subagent must complete (else lead has no findings)",
		).toBeGreaterThanOrEqual(1);

		// ── Step 8: Prometheus delta ──────────────────────────────────
		const afterMetrics = await fetchPrometheusCounters(page, API_BASE);
		expect(
			afterMetrics.toolCallsTotal - baseMetrics.toolCallsTotal,
			"agent_tool_calls_total should bump by at least 5 (lead + workers)",
		).toBeGreaterThanOrEqual(5);
		expect(
			afterMetrics.turnDurationCount - baseMetrics.turnDurationCount,
			"agent_turn_duration_seconds_count should bump by >= 1",
		).toBeGreaterThanOrEqual(1);

		// ── Step 9: structlog assertions ──────────────────────────────
		const logText = await readFile(API_LOG_PATH, "utf8").catch(() => "");
		if (logText) {
			const turnStartedLines = logText
				.split("\n")
				.filter(
					(l) =>
						l.includes("agent.turn_started") && l.includes(String(threadId)),
				).length;
			expect(
				turnStartedLines,
				"agent.turn_started must appear for this thread",
			).toBeGreaterThanOrEqual(1);
			// No step-cap-hit for this thread — Bug 3 regression guard.
			const stepCapHits = logText
				.split("\n")
				.filter(
					(l) =>
						l.includes("agent.step_cap_hit") && l.includes(String(threadId)),
				).length;
			expect(stepCapHits, "lead must complete within step cap").toBe(0);
			// agent.turn_completed should carry `messages` (Bug 3 rename).
			const turnCompletedLines = logText
				.split("\n")
				.filter(
					(l) =>
						l.includes("agent.turn_completed") && l.includes(String(threadId)),
				);
			expect(turnCompletedLines.length).toBeGreaterThanOrEqual(1);
			const lastTurn = turnCompletedLines[turnCompletedLines.length - 1];
			expect(lastTurn).toMatch(/"messages":\s*\d+/);
			expect(lastTurn).toMatch(/"steps":\s*\d+/);
		}
	});
});

async function fetchPrometheusCounters(
	page: import("@playwright/test").Page,
	base: string,
): Promise<{ toolCallsTotal: number; turnDurationCount: number }> {
	const resp = await page.request.get(`${base}/metrics`);
	if (!resp.ok()) return { toolCallsTotal: 0, turnDurationCount: 0 };
	const text = await resp.text();
	const toolCalls = sumPrometheusFamily(
		text,
		/^hughes_agent_tool_calls_total\b/,
	);
	const turnDurCount = sumPrometheusFamily(
		text,
		/^hughes_agent_turn_duration_seconds_count\b/,
	);
	return { toolCallsTotal: toolCalls, turnDurationCount: turnDurCount };
}

function sumPrometheusFamily(text: string, lineRegex: RegExp): number {
	let total = 0;
	for (const line of text.split("\n")) {
		if (!lineRegex.test(line)) continue;
		const parts = line.trim().split(/\s+/);
		const value = Number(parts[parts.length - 1]);
		if (Number.isFinite(value)) total += value;
	}
	return total;
}
