import { expect, test } from "@playwright/test";

const QUESTIONS = [
	"How many loans were originated last month?",
	"What is the past-due ratio by branch?",
	"Show top depositors over $1M",
] as const;

function answerFor(q: string) {
	return {
		request_id: `r-${q.length}`,
		question: q,
		sql: "select 1",
		explanation: `Answer for: ${q}`,
		tables_used: [],
		assumptions: [],
		caveats: [],
		rows: [],
		columns: [],
		clarification: null,
	};
}

test("chat thread keeps three consecutive questions visible (HUG-132)", async ({
	page,
}) => {
	await page.route("**/api/ask", async (route) => {
		const body = JSON.parse(route.request().postData() ?? "{}");
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(answerFor(body.question)),
		});
	});
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

	await page.goto("/chat");
	await expect(page.getByRole("heading", { name: "Hughes AI" })).toBeVisible();

	const input = page.getByPlaceholder("Ask a question about lending…");
	const askBtn = page.getByRole("button", { name: "Ask" });

	for (const q of QUESTIONS) {
		await input.fill(q);
		await askBtn.click();
		await expect(page.getByText(`Answer for: ${q}`)).toBeVisible();
	}

	const log = page.getByRole("log", { name: "Conversation" });
	for (const q of QUESTIONS) {
		await expect(log.getByText(q, { exact: true })).toBeVisible();
		await expect(log.getByText(`Answer for: ${q}`)).toBeVisible();
	}

	await expect(log.getByLabel("User question")).toHaveCount(3);
	await expect(log.getByLabel("Assistant answer")).toHaveCount(3);
});
