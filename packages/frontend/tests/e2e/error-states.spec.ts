import { expect, test } from "@playwright/test";

async function submitQuestion(
	page: import("@playwright/test").Page,
	question = "How many loans?",
) {
	await page.getByPlaceholder("Ask a question about lending…").fill(question);
	await page.getByRole("button", { name: "Ask" }).click();
}

test.describe("ask — error states", () => {
	test("shows HTTP 500 alert when API returns server error", async ({ page }) => {
		await page.route("**/api/ask", async (route) => {
			await route.fulfill({
				status: 500,
				contentType: "application/json",
				body: "{}",
			});
		});

		await page.goto("/chat");
		await submitQuestion(page);

		const alert = page.getByRole("alert");
		await expect(alert).toBeVisible();
		await expect(alert).toHaveText("HTTP 500");
	});

	test("shows error alert when network request is aborted", async ({ page }) => {
		await page.route("**/api/ask", async (route) => {
			await route.abort();
		});

		await page.goto("/chat");
		await submitQuestion(page);

		const alert = page.getByRole("alert");
		await expect(alert).toBeVisible();
		await expect(alert).not.toBeEmpty();
	});
});
