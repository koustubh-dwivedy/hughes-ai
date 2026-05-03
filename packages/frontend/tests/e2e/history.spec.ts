import { expect, test } from "@playwright/test";

const HIST_ID = "hist-uuid-1";

const HISTORY_LIST = [
	{
		id: HIST_ID,
		question: "How many loans were funded?",
		sql: "SELECT COUNT(*) FROM fct_loan_originations",
		created_at: "2026-04-25T10:00:00Z",
	},
];

const HISTORY_DETAIL = {
	id: HIST_ID,
	question: "How many loans were funded?",
	sql: "SELECT COUNT(*) FROM fct_loan_originations",
	created_at: "2026-04-25T10:00:00Z",
	answer_json: {
		explanation: "Counts all funded loans in the originations table.",
		rows: [{ loan_count: 288 }],
		columns: ["loan_count"],
	},
	assumptions: [],
	caveats: ["Only includes matched funded loans."],
	lineage_json: { tables_used: ["fct_loan_originations"] },
};

async function interceptHistory(page: import("@playwright/test").Page) {
	await page.route("**/api/**", async (route) => {
		const url = new URL(route.request().url());
		const method = route.request().method();
		const p = url.pathname;

		if (p === "/api/history" && method === "GET") {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(HISTORY_LIST),
			});
		} else if (p === `/api/history/${HIST_ID}` && method === "GET") {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(HISTORY_DETAIL),
			});
		} else {
			await route.continue();
		}
	});
}

test.describe("history surfaces", () => {
	test("clicking a question in the drawer loads its result", async ({
		page,
	}) => {
		await interceptHistory(page);
		await page.goto("/intelligence");

		await page
			.getByRole("button", { name: "Open conversation history" })
			.click();
		const drawer = page.getByRole("dialog", { name: "Conversation history" });
		await expect(
			drawer.getByText("How many loans were funded?"),
		).toBeVisible();

		await drawer.getByText("How many loans were funded?").click();

		await expect(
			page.getByText("Counts all funded loans in the originations table."),
		).toBeVisible();
	});
});
