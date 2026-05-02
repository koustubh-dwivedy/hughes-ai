import { expect, test } from "@playwright/test";

const ITEMS = [
	{
		id: "id-1",
		question: "What is the past-due ratio?",
		sql: "SELECT 1",
		created_at: "2026-05-02T13:00:00Z",
	},
	{
		id: "id-2",
		question: "How many active loans?",
		sql: "SELECT 2",
		created_at: "2026-05-02T09:30:00Z",
	},
	{
		id: "id-3",
		question: "Top branches by deposits",
		sql: "SELECT 3",
		created_at: "2026-05-01T14:00:00Z",
	},
];

const DETAIL = {
	id: "id-2",
	question: "How many active loans?",
	sql: "SELECT count(*) FROM loans",
	created_at: "2026-05-02T09:30:00Z",
	answer_json: {
		explanation: "There are 1,234 active loans.",
		columns: ["count"],
		rows: [{ count: 1234 }],
	},
	assumptions: [],
	caveats: [],
	lineage_json: { tables_used: [] },
};

test.beforeEach(async ({ page }) => {
	await page.route(/\/api\/history\?[^/]*$/, (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(ITEMS),
		}),
	);
	await page.route("**/api/history/id-2", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(DETAIL),
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
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
	);
});

test("HistoryRail groups items by day in the sidebar (HUG-137)", async ({
	page,
}) => {
	await page.goto("/chat");
	const rail = page.getByRole("complementary", { name: "Conversation history" });
	await expect(rail).toBeVisible();
	await expect(rail.getByRole("heading", { name: "Today", level: 3 })).toBeVisible();
	await expect(
		rail.getByRole("heading", { name: "Yesterday", level: 3 }),
	).toBeVisible();
	await expect(rail.getByText("What is the past-due ratio?")).toBeVisible();
});

test("Search field filters history items", async ({ page }) => {
	await page.goto("/chat");
	const rail = page.getByRole("complementary", { name: "Conversation history" });
	await expect(rail.getByText("Top branches by deposits")).toBeVisible();
	await rail.getByLabel("Search history").fill("branches");
	await expect(rail.getByText("Top branches by deposits")).toBeVisible();
	await expect(rail.getByText("How many active loans?")).not.toBeVisible();
});

test("Clicking a history item loads the conversation in chat", async ({
	page,
}) => {
	await page.goto("/chat");
	const rail = page.getByRole("complementary", { name: "Conversation history" });
	await rail.getByText("How many active loans?").click();
	await expect(
		page.getByRole("log", { name: "Conversation" }),
	).toBeVisible();
	await expect(page.getByText("There are 1,234 active loans.")).toBeVisible();
});
