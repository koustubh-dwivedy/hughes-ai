import { expect, test, type Route } from "@playwright/test";
import { buildFinalEvent, defaultStepLeadIn, formatSse } from "./_helpers/sse";

const THREAD_ID = "11111111-2222-3333-4444-555555555555";

interface AgentTurn {
	matchContent: RegExp;
	summary: string;
	openuiDsl?: string;
}

/**
 * Install routes that mock the threads API surface so the e2e doesn't
 * depend on a running backend or the agent's latency. The fake server:
 *  - POST /threads creates a stable id
 *  - GET /threads/:id returns the persisted message log assembled from
 *    every turn the test has run so far
 *  - POST /threads/:id/messages streams the lead-in step events and a
 *    matching final event (selected by the user-content regex)
 */
async function installThreadsMock(
	page: import("@playwright/test").Page,
	turns: AgentTurn[],
): Promise<void> {
	const persisted: Array<Record<string, unknown>> = [];

	await page.route("**/api/threads", async (route: Route) => {
		const method = route.request().method();
		if (method === "POST") {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					thread_id: THREAD_ID,
					title: null,
					started_at: new Date().toISOString(),
				}),
			});
			return;
		}
		// GET /threads — list
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({
				threads: [
					{
						thread_id: THREAD_ID,
						title: null,
						started_at: new Date().toISOString(),
						last_active_at: new Date().toISOString(),
					},
				],
			}),
		});
	});

	await page.route(`**/api/threads/${THREAD_ID}`, async (route: Route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({
				thread_id: THREAD_ID,
				title: null,
				started_at: new Date().toISOString(),
				last_active_at: new Date().toISOString(),
				messages: persisted,
			}),
		});
	});

	await page.route(
		`**/api/threads/${THREAD_ID}/messages`,
		async (route: Route) => {
			const post = route.request().postDataJSON() as { content: string };
			const turn = turns.find((t) => t.matchContent.test(post.content));
			if (!turn) {
				await route.fulfill({ status: 500, body: "no canned turn" });
				return;
			}
			persisted.push({
				message_id: `u-${persisted.length}`,
				thread_id: THREAD_ID,
				parent_message_id: null,
				role: "user",
				content: post.content,
				tool_calls: null,
				tool_results: null,
				openui_dsl: null,
				mf_query: null,
				rows: null,
				created_at: new Date().toISOString(),
			});
			const final = buildFinalEvent({
				threadId: THREAD_ID,
				messageId: `t-${persisted.length}`,
				summary: turn.summary,
				openuiDsl: turn.openuiDsl,
			});
			persisted.push(final.data.message as Record<string, unknown>);
			const body = formatSse([...defaultStepLeadIn(), final]);
			await route.fulfill({
				status: 200,
				contentType: "text/event-stream",
				body,
			});
		},
	);
}

test.describe("intelligence conversational UI (HUG-179)", () => {
	test("ask, follow-up, and stacked-bar render in sequence", async ({
		page,
	}) => {
		await installThreadsMock(page, [
			{
				matchContent: /delinquency/i,
				summary: "Past-due ratio is 9.8% as of April 2026.",
				openuiDsl:
					'root = Stack([kpi])\nkpi = TextContent("9.8%", "large-heavy")',
			},
			{
				matchContent: /branch/i,
				summary: "Past-due ratio by branch:",
				openuiDsl:
					'root = Stack([chart])\nchart = BarChart(["North","South"], [series], "Branch", "Ratio")\nseries = Series("ratio", [0.05, 0.12])',
			},
			{
				matchContent: /stacked/i,
				summary: "Same data, stacked:",
				openuiDsl:
					'root = Stack([chart])\nchart = SingleStackedBarChart(["North","South"], [s1,s2])\ns1 = Series("30-59", [0.02, 0.04])\ns2 = Series("60+", [0.03, 0.08])',
			},
		]);
		await page.goto("/intelligence");
		const composer = page.getByLabel("Ask Hughes");
		await composer.fill("What's our delinquency rate this month?");
		await page.getByRole("button", { name: "Send" }).click();

		await expect(
			page.getByText("Past-due ratio is 9.8% as of April 2026."),
		).toBeVisible();
		await expect(page.getByTestId("openui-renderer").first()).toBeVisible();

		await composer.fill("Break that down by branch");
		await page.getByRole("button", { name: "Send" }).click();
		await expect(page.getByText("Past-due ratio by branch:")).toBeVisible();

		await composer.fill("Show that as a stacked bar");
		await page.getByRole("button", { name: "Send" }).click();
		await expect(page.getByText("Same data, stacked:")).toBeVisible();

		// Three OpenUI trees rendered (one per assistant turn).
		await expect(page.getByTestId("openui-renderer")).toHaveCount(3);
	});

	test("hydrates messages from URL on reload", async ({ page }) => {
		await installThreadsMock(page, [
			{
				matchContent: /loan-to-deposit/i,
				summary: "LTD ratio is 13.48%.",
				openuiDsl: 'root = TextContent("13.48%", "large-heavy")',
			},
		]);
		await page.goto("/intelligence");
		await page.getByLabel("Ask Hughes").fill("What's the loan-to-deposit ratio?");
		await page.getByRole("button", { name: "Send" }).click();
		await expect(page.getByText("LTD ratio is 13.48%.")).toBeVisible();

		// Reload the page; the URL should now point at the thread id.
		await expect(page).toHaveURL(new RegExp(`/intelligence/${THREAD_ID}$`));
		await page.reload();
		await expect(page.getByText("What's the loan-to-deposit ratio?"))
			.toBeVisible();
		await expect(page.getByText("LTD ratio is 13.48%.")).toBeVisible();
		await expect(page.getByTestId("openui-renderer")).toBeVisible();
	});
});
