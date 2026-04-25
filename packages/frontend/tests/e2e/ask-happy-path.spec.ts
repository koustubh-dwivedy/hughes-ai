import { expect, test } from "@playwright/test";

test.describe("ask — happy path", () => {
	test.setTimeout(90_000); // LLM call can take up to 30s; buffer for Vite start

	test("submits a question and renders result + history", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByRole("heading", { name: "Hughes AI" })).toBeVisible();

		const input = page.getByPlaceholder("Ask a question about lending…");
		const askBtn = page.getByRole("button", { name: "Ask" });

		// Button disabled until text is entered
		await expect(askBtn).toBeDisabled();

		await input.fill("How many loan applications are there?");
		await expect(askBtn).toBeEnabled();
		await askBtn.click();

		// Loading state appears
		await expect(page.getByRole("button", { name: "Loading…" })).toBeVisible();

		// Result section appears (wait up to 60s for LLM + DB)
		const section = page.locator("section");
		await expect(section).toBeVisible({ timeout: 60_000 });

		// Explanation paragraph is present and non-empty
		const explanation = section.locator("p").first();
		await expect(explanation).not.toBeEmpty();

		// Data table rendered (COUNT → one numeric column → table path)
		await expect(section.locator("table")).toBeVisible();

		// SQL disclosure present (may be collapsed — just check it exists)
		await expect(
			section.locator("details summary", { hasText: "SQL" }),
		).toBeVisible();

		// History panel updated with the submitted question
		// Filter by heading text — TrustPanel is also an <aside>
		const historyPanel = page.locator("aside").filter({ hasText: "History" });
		await expect(historyPanel).toBeVisible();
		await expect(
			historyPanel
				.getByRole("button", {
					name: "How many loan applications are there?",
				})
				.first(),
		).toBeVisible();
	});
});
