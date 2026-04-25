import { expect, test } from "@playwright/test";

const CLARIFICATION_RESPONSE = {
	request_id: "test-clarification-id",
	question: "Show me rates",
	sql: null,
	explanation: null,
	tables_used: [],
	assumptions: [],
	caveats: [],
	rows: [],
	columns: [],
	clarification:
		"Your question could refer to multiple metrics: approval rate or delinquency rate. Which one are you asking about?",
};

test.describe("ask — clarification flow", () => {
	test("shows clarification text and suppresses result section", async ({
		page,
	}) => {
		// Register intercept before navigation so it catches the first request
		await page.route("**/api/ask", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(CLARIFICATION_RESPONSE),
			});
		});

		await page.goto("/");
		await expect(
			page.getByRole("heading", { name: "Hughes AI" }),
		).toBeVisible();

		await page
			.getByPlaceholder("Ask a question about lending…")
			.fill("Show me rates");
		await page.getByRole("button", { name: "Ask" }).click();

		// Clarification text appears as a paragraph
		await expect(
			page.getByText("Your question could refer to multiple metrics"),
		).toBeVisible();

		// No result section — clarification short-circuits the normal answer path
		await expect(page.locator("section")).not.toBeVisible();
	});
});
