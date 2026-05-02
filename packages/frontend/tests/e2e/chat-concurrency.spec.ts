/**
 * HUG-157: chat concurrency.
 *
 *   1. Double-clicking Ask must NOT submit twice — the button
 *      disables while the mutation is in flight.
 *   2. Submitting question B while question A is still streaming
 *      must produce both Q and both A in the thread (no lost
 *      messages, no swapped order). The current impl doesn't
 *      cancel A's API; instead both end up in the thread, which
 *      is the right user-visible behaviour.
 *   3. Rapid-fire 5 questions in a row must all land in the
 *      thread with their answers, in order.
 */

import { expect, test } from "@playwright/test";

function answerFor(q: string) {
	return {
		request_id: `r-${q.length}-${Date.now()}`,
		question: q,
		sql: "select 1",
		explanation: `Answer: ${q.length} chars`,
		tables_used: [],
		assumptions: [],
		caveats: [],
		rows: [],
		columns: [],
		clarification: null,
	};
}

// Sets up auxiliary routes only (history, trust). /api/ask is left to
// each test so the per-test counter handler isn't shadowed by another
// matching route registered later in the chain (Playwright is LIFO).
async function setupAuxRoutes(page: import("@playwright/test").Page) {
	await page.route("**/api/history**", (r) =>
		r.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
	);
	await page.route("**/api/trust**", (r) =>
		r.fulfill({
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
}

test("double-clicking Ask does not double-submit", async ({ page }) => {
	let askCount = 0;
	await page.route("**/api/ask", async (route) => {
		askCount++;
		const body = JSON.parse(route.request().postData() ?? "{}");
		// Slow enough that two clicks could in theory race
		await new Promise((r) => setTimeout(r, 400));
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(answerFor(body.question)),
		});
	});
	await setupAuxRoutes(page);

	await page.goto("/chat");
	const input = page.getByPlaceholder("Ask a question about lending…");
	const askBtn = page.getByRole("button", { name: "Ask" });

	await input.fill("First question");
	// Two clicks back-to-back — the second should hit a disabled button
	await Promise.all([askBtn.click(), askBtn.click().catch(() => {})]);

	// Wait for the answer to land
	await expect(page.getByRole("log", { name: "Conversation" })).toBeVisible();
	await expect(page.getByText("Answer: 14 chars")).toBeVisible();

	// Exactly one /api/ask call
	expect(askCount).toBe(1);

	// Exactly one user-question card in the thread
	await expect(
		page.getByRole("log", { name: "Conversation" }).getByLabel("User question"),
	).toHaveCount(1);
});

test("submitting B while A is in-flight produces both Q+A pairs", async ({
	page,
}) => {
	const seenQuestions: string[] = [];
	await page.route("**/api/ask", async (route) => {
		const body = JSON.parse(route.request().postData() ?? "{}");
		seenQuestions.push(body.question);
		// Stagger the responses so B's request arrives during A's wait
		const delay = body.question === "First" ? 600 : 100;
		await new Promise((r) => setTimeout(r, delay));
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(answerFor(body.question)),
		});
	});
	await setupAuxRoutes(page);

	await page.goto("/chat");
	const input = page.getByPlaceholder("Ask a question about lending…");
	const askBtn = page.getByRole("button", { name: "Ask" });

	await input.fill("First");
	await askBtn.click();
	// Wait for A's answer before submitting B (button re-enables)
	await expect(page.getByText("Answer: 5 chars")).toBeVisible();

	await input.fill("Second longer one");
	await page.getByRole("button", { name: "Ask" }).click();
	await expect(page.getByText("Answer: 17 chars")).toBeVisible();

	// Both questions reached the API
	expect(seenQuestions).toEqual(["First", "Second longer one"]);

	// Both Q+A pairs in the thread, in the right order
	const log = page.getByRole("log", { name: "Conversation" });
	await expect(log.getByLabel("User question")).toHaveCount(2);
	await expect(log.getByLabel("Assistant answer")).toHaveCount(2);
});

test("rapid-fire 5 questions all land with answers in order", async ({
	page,
}) => {
	const askCount: { n: number } = { n: 0 };
	await page.route("**/api/ask", async (route) => {
		askCount.n++;
		const body = JSON.parse(route.request().postData() ?? "{}");
		// Short response so we burn through 5 quickly
		await new Promise((r) => setTimeout(r, 50));
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(answerFor(body.question)),
		});
	});
	await setupAuxRoutes(page);

	await page.goto("/chat");
	const input = page.getByPlaceholder("Ask a question about lending…");
	const askBtn = page.getByRole("button", { name: "Ask" });

	const questions = ["alpha", "beta", "gamma", "delta", "epsilon"];
	for (const q of questions) {
		await input.fill(q);
		await askBtn.click();
		// Wait for the answer to land before firing the next one
		await expect(
			page.getByText(`Answer: ${q.length} chars`).last(),
		).toBeVisible();
	}

	expect(askCount.n).toBe(5);

	const log = page.getByRole("log", { name: "Conversation" });
	await expect(log.getByLabel("User question")).toHaveCount(5);
	await expect(log.getByLabel("Assistant answer")).toHaveCount(5);
});
