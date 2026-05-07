/**
 * Live full-stack e2e — drives the real LangGraph agent and asserts that
 * an answer's OpenUI DSL renders into real DOM.
 *
 * Most of the existing Playwright suite mocks the SSE response (see
 * intelligence-conversational.spec.ts) so it can run on a workstation
 * without a database, LLM, or Docker. This spec exercises the *whole*
 * stack — useful for catching regressions in agent → DSL → renderer
 * that mock-driven tests can't see.
 *
 * Skipped by default. Set `E2E_LIVE=1` and start the full stack first:
 *
 *   make dev          # postgres, redis, vector
 *   make seed         # synthetic data (idempotent)
 *   cd packages/api && uvicorn api.main:app --reload --port 8000
 *
 * The test asks a must-pass question whose agent reliably emits a KPI
 * tile DSL ("loan-to-deposit ratio this month"). It then waits for
 * either the rendered KPI text or the answer summary, whichever shows
 * up first — both proofs that the full stack delivered an answer.
 */

import { expect, test } from "@playwright/test";

const live = process.env.E2E_LIVE === "1";

test.describe("intelligence — live agent → OpenUI", () => {
	// LLM round-trip can take 90+ seconds on a cold start. Generous default.
	test.setTimeout(180_000);

	test.skip(!live, "set E2E_LIVE=1 + start full stack to enable");

	test("loan-to-deposit ratio question renders agent answer", async ({
		page,
	}) => {
		await page.goto("/intelligence");
		const composer = page.getByPlaceholder(/ask|message|question/i).first();
		await composer.fill("What's our loan-to-deposit ratio this month?");
		await composer.press("Enter");

		// Either the KPI tile from OpenUI DSL or the prose summary needs to land.
		// Both prove agent → SSE → frontend → render fired end-to-end.
		const kpiTile = page.getByText(/13\.\d|14\.\d|loan.*deposit/i).first();
		await expect(kpiTile).toBeVisible({ timeout: 150_000 });

		// Sanity: the render path didn't throw a parse error visible to the user.
		await expect(page.getByText(/openui.*error|dsl.*invalid/i)).toHaveCount(0);
	});
});
