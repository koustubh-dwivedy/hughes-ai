import { expect, test } from "@playwright/test";

const ANSWER = {
	request_id: "r-1",
	question: "How many active loans do we have?",
	sql: "select 1",
	explanation: "We have 1,234 active loans.",
	tables_used: [],
	assumptions: [],
	caveats: [],
	rows: [],
	columns: [],
	clarification: null,
};

test.beforeEach(async ({ page }) => {
	await page.route("**/api/history**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
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
});

test("empty chat shows 6 suggested prompts (HUG-136)", async ({ page }) => {
	await page.goto("/chat");
	const region = page.getByRole("region", { name: "Suggested prompts" });
	await expect(region).toBeVisible();
	await expect(region.getByRole("button")).toHaveCount(6);
});

test("clicking a suggested prompt submits it and shows the answer", async ({
	page,
}) => {
	let postedQuestion = "";
	await page.route("**/api/ask", async (route) => {
		const body = JSON.parse(route.request().postData() ?? "{}");
		postedQuestion = body.question;
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ ...ANSWER, question: body.question }),
		});
	});

	await page.goto("/chat");
	const firstChip = page
		.getByRole("region", { name: "Suggested prompts" })
		.getByRole("button")
		.first();
	const chipText = await firstChip.textContent();
	await firstChip.click();

	await expect(
		page.getByRole("log", { name: "Conversation" }),
	).toBeVisible();
	expect(postedQuestion).toBe(chipText?.trim() ?? "");
	await expect(page.getByText("We have 1,234 active loans.")).toBeVisible();
});
