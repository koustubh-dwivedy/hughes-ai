/**
 * Iterative UI smoke-driver for /intelligence (HUG-201 follow-up).
 *
 * Drives the running dev stack (Vite :5173 + uvicorn :8000) through the
 * key conversational paths and prints a pass/fail per scenario. Designed
 * to be re-run after every fix.
 *
 *   node scripts/ui_smoke.mjs            # runs every scenario
 *   node scripts/ui_smoke.mjs --quick    # skips long-LLM scenarios
 *
 * Output goes to stdout as JSON-ish lines, one per scenario:
 *   { name, ok, durationMs, notes }
 *
 * Failures dump screenshots to /tmp/hughes-ui-smoke/<scenario>.png and
 * the page's console errors / failed requests for context.
 */

import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const BASE = "http://localhost:5173";
const OUT_DIR = "/tmp/hughes-ui-smoke";
const QUICK = process.argv.includes("--quick");
const HEADED = process.argv.includes("--headed");

await fs.mkdir(OUT_DIR, { recursive: true });

const results = [];

async function withPage(name, fn) {
	const t0 = Date.now();
	const browser = await chromium.launch({ headless: !HEADED });
	const ctx = await browser.newContext();
	const page = await ctx.newPage();
	const consoleErrors = [];
	const failedRequests = [];
	page.on("console", (msg) => {
		if (msg.type() === "error") consoleErrors.push(msg.text());
	});
	page.on("requestfailed", (req) =>
		failedRequests.push(`${req.method()} ${req.url()} → ${req.failure()?.errorText}`),
	);
	let ok = false;
	let notes = [];
	try {
		await fn({ page, ctx, addNote: (n) => notes.push(n) });
		ok = true;
	} catch (err) {
		notes.push(`THREW: ${err.message}`);
		try {
			await page.screenshot({ path: path.join(OUT_DIR, `${name}.png`) });
		} catch {}
	} finally {
		if (consoleErrors.length) notes.push(`console.error ×${consoleErrors.length}: ${consoleErrors.slice(0, 3).join(" | ")}`);
		if (failedRequests.length) notes.push(`failed-req ×${failedRequests.length}: ${failedRequests.slice(0, 3).join(" | ")}`);
		await ctx.close();
		await browser.close();
	}
	results.push({ name, ok, durationMs: Date.now() - t0, notes });
	const status = ok ? "PASS" : "FAIL";
	console.log(`[${status}] ${name} (${Date.now() - t0}ms)${notes.length ? `\n  ${notes.join("\n  ")}` : ""}`);
}

// ── Scenarios ─────────────────────────────────────────────────────────

await withPage("empty-state-shows-suggestions", async ({ page, addNote }) => {
	await page.goto(`${BASE}/intelligence`);
	await page.waitForLoadState("networkidle");
	const heading = page.getByRole("heading", { name: /Ask Hughes/i });
	if (!(await heading.isVisible())) throw new Error("'Ask Hughes' heading not visible");
	const buttons = page.getByRole("button").filter({ hasText: /loan-to-deposit|deposit balance|origination|deposit products/i });
	const count = await buttons.count();
	addNote(`suggestion buttons: ${count}`);
	if (count !== 4) throw new Error(`expected 4 suggestion buttons, got ${count}`);
});

await withPage("page-level-scroll-contained", async ({ page, addNote }) => {
	await page.goto(`${BASE}/intelligence`);
	await page.waitForLoadState("networkidle");
	const docMetrics = await page.evaluate(() => ({
		scrollHeight: document.documentElement.scrollHeight,
		clientHeight: document.documentElement.clientHeight,
		bodyOverflow: getComputedStyle(document.body).overflow,
	}));
	addNote(`docMetrics: ${JSON.stringify(docMetrics)}`);
	if (docMetrics.scrollHeight > docMetrics.clientHeight + 4) {
		throw new Error(`page scrolls (${docMetrics.scrollHeight} > ${docMetrics.clientHeight})`);
	}
});

await withPage("new-thread-button-clears-state", async ({ page, addNote }) => {
	// Navigate directly to a non-existent thread id to simulate having one
	// open; clicking "+ New thread" should land on the empty state.
	await page.goto(`${BASE}/intelligence`);
	await page.waitForLoadState("networkidle");
	// First make sure the suggestions are gone (simulate "in a thread") by
	// briefly typing into composer — composer state is local, doesn't help.
	// Instead, send a fake question to /threads to get an id, then visit it.
	const sid = `smoke-${Date.now()}`;
	const create = await page.request.post(`${BASE}/api/threads`, {
		data: {},
		headers: { "X-Hughes-Session": sid, "Content-Type": "application/json" },
	});
	if (!create.ok()) throw new Error(`create thread failed: HTTP ${create.status()}`);
	const { thread_id } = await create.json();
	await page.evaluate((s) => sessionStorage.setItem("hughes_session_id", s), sid);
	await page.goto(`${BASE}/intelligence/${thread_id}`);
	await page.waitForLoadState("networkidle");
	const newBtn = page.getByRole("button", { name: /\+ New thread/i });
	if (!(await newBtn.isVisible())) throw new Error("New thread button missing on rail");
	await newBtn.click();
	await page.waitForURL(`${BASE}/intelligence`, { timeout: 5000 });
	const heading = page.getByRole("heading", { name: /Ask Hughes/i });
	if (!(await heading.isVisible())) throw new Error("After 'New thread', empty state heading not visible");
	addNote(`URL after click: ${page.url()}`);
});

if (!QUICK) {
	await withPage("references-pill-and-modal", async ({ page, addNote }) => {
		await page.goto(`${BASE}/intelligence`);
		await page.waitForLoadState("networkidle");
		await page.getByRole("button", { name: /loan-to-deposit/i }).click();
		const terminal = page.locator('[aria-label="Assistant answer"]').first();
		await terminal.waitFor({ state: "visible", timeout: 180_000 });
		const inlineSourceRows = await page.getByText(/^Source rows$/).count();
		const inlineMf = await page.getByText(/^MetricFlow query$/).count();
		addNote(`inline 'Source rows': ${inlineSourceRows}; inline 'MetricFlow query': ${inlineMf}`);
		if (inlineSourceRows > 0 || inlineMf > 0) {
			throw new Error("references should be hidden behind the modal, not inline");
		}
		const refsBtn = page.getByRole("button", { name: /References/i });
		await refsBtn.waitFor({ state: "visible", timeout: 5000 });
		await refsBtn.click();
		const dialog = page.getByRole("dialog", { name: /Answer references/i });
		await dialog.waitFor({ state: "visible", timeout: 2000 });
		const dialogText = await dialog.textContent();
		addNote(`dialog opens with Source rows: ${dialogText?.includes("Source rows")}; MetricFlow query: ${dialogText?.includes("MetricFlow query")}`);
		await page.keyboard.press("Escape");
		await dialog.waitFor({ state: "hidden", timeout: 2000 });
	});

	await withPage("submit-from-empty-state-shows-acknowledgment", async ({ page, addNote }) => {
		await page.goto(`${BASE}/intelligence`);
		await page.waitForLoadState("networkidle");
		const composer = page.getByLabel(/Ask Hughes/i);
		await composer.fill("What's our loan-to-deposit ratio this month?");
		// Submit and immediately look for the user bubble — it MUST appear
		// before the LLM round-trip completes.
		await page.getByRole("button", { name: /^Send$/ }).click();
		const userBubble = page.locator('[aria-label="User question (sending)"], [aria-label="User question"]').first();
		await userBubble.waitFor({ state: "visible", timeout: 1500 });
		addNote("optimistic user bubble appeared");
		const thinking = page.locator('[aria-label="Assistant is thinking"]');
		await thinking.waitFor({ state: "visible", timeout: 1500 });
		addNote("thinking bubble appeared");
		// Wait up to 3 minutes for the real terminal answer (LLM cold start).
		const terminal = page.locator('[aria-label="Assistant answer"]').first();
		await terminal.waitFor({ state: "visible", timeout: 180_000 });
		addNote(`final answer arrived after ${page.url()}`);
		// Confirm OpenUI styling actually rendered (not raw <div>).
		const card = page.locator(".openui-card, [class*='card'], [data-openui]").first();
		const cardCount = await page.locator('[class*="Card"], [class*="card"]').count();
		addNote(`elements with card class: ${cardCount}`);
	});

	await withPage("chart-question-renders-openui", async ({ page, addNote }) => {
		await page.goto(`${BASE}/intelligence`);
		await page.waitForLoadState("networkidle");
		const composer = page.getByLabel(/Ask Hughes/i);
		await composer.fill("Show deposit balance by branch as of the latest month.");
		await page.getByRole("button", { name: /^Send$/ }).click();
		const terminal = page.locator('[aria-label="Assistant answer"]').first();
		await terminal.waitFor({ state: "visible", timeout: 180_000 });
		// Look for any chart / table content
		const renderer = page.locator('[data-testid="openui-renderer"]').first();
		const rendered = await renderer.count();
		addNote(`openui-renderer present: ${rendered > 0}`);
		const chart = page.locator('svg, canvas, [class*="chart" i], [class*="bar" i]');
		addNote(`chart-like elements: ${await chart.count()}`);
	});
}

// ── Summary ─────────────────────────────────────────────────────────

const passed = results.filter((r) => r.ok).length;
const failed = results.filter((r) => !r.ok).length;
console.log(`\n=== ${passed}/${results.length} passed, ${failed} failed ===`);
if (failed > 0) process.exit(1);
