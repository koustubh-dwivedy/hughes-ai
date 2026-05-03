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
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
	);
});

test("Recent questions card renders on the Data Intelligence empty state", async ({
	page,
}) => {
	await page.goto("/intelligence");
	const recent = page.getByRole("region", { name: "Recent questions" });
	await expect(recent).toBeVisible();
	await expect(
		recent.getByText("What is the past-due ratio?"),
	).toBeVisible();
	await expect(recent.getByText("Top branches by deposits")).toBeVisible();
});

test("Clicking the clock button opens the history drawer", async ({ page }) => {
	await page.goto("/intelligence");
	await page
		.getByRole("button", { name: "Open conversation history" })
		.click();
	const drawer = page.getByRole("dialog", { name: "Conversation history" });
	await expect(drawer).toBeVisible();
	await expect(drawer.getByText("How many active loans?")).toBeVisible();
});

test("Clicking a recent question loads the conversation in chat", async ({
	page,
}) => {
	await page.goto("/intelligence");
	const recent = page.getByRole("region", { name: "Recent questions" });
	await recent.getByText("How many active loans?").click();
	await expect(
		page.getByRole("log", { name: "Conversation" }),
	).toBeVisible();
	await expect(page.getByText("There are 1,234 active loans.")).toBeVisible();
});
