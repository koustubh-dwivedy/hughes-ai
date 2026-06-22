import { expect, test } from "@playwright/test";

// Return empty JSON for all dashboard data calls — headings render regardless
test.beforeEach(async ({ page }) => {
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: "{}",
		}),
	);
});

test.describe("navigation", () => {
	test("/ shows the launchpad and enters Business Intelligence", async ({
		page,
	}) => {
		await page.goto("/");
		await expect(page).toHaveURL("/");
		await expect(
			page.getByRole("button", { name: "Business Intelligence" }),
		).toBeVisible();
		await expect(
			page.getByRole("button", { name: "Dispute Center" }),
		).toBeVisible();
		await page.getByRole("button", { name: "Business Intelligence" }).click();
		await expect(page).toHaveURL("/dashboards/executive");
		await expect(
			page.getByRole("heading", { name: "Executive Summary" }),
		).toBeVisible();
	});

	test("clicking each nav item navigates in sequence", async ({ page }) => {
		await page.goto("/dashboards/executive");

		await page.getByRole("link", { name: "Deposit Portfolio" }).click();
		await expect(page).toHaveURL("/dashboards/deposits");
		await expect(
			page.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeVisible();

		await page.getByRole("link", { name: "Past Due" }).click();
		await expect(page).toHaveURL("/dashboards/past-due");
		await expect(
			page.getByRole("heading", { name: "Past Due", exact: true }),
		).toBeVisible();

		await page.getByRole("link", { name: "Officer/Branch" }).click();
		await expect(page).toHaveURL("/dashboards/officer-branch");
		await expect(
			page.getByRole("heading", { name: "Officer / Branch Loans" }),
		).toBeVisible();

		await page.getByRole("link", { name: "Data Intelligence" }).click();
		await expect(page).toHaveURL("/intelligence");
		await expect(page.getByRole("textbox")).toBeVisible();

		await page.getByRole("link", { name: "Executive Summary" }).click();
		await expect(page).toHaveURL("/dashboards/executive");
		await expect(
			page.getByRole("heading", { name: "Executive Summary" }),
		).toBeVisible();
	});

	test("active nav item reflects current route", async ({ page }) => {
		await page.goto("/dashboards/deposits");
		const depositLink = page.getByRole("link", { name: "Deposit Portfolio" });
		await expect(depositLink).toHaveAttribute("aria-current", "page");

		await page.getByRole("link", { name: "Past Due" }).click();
		await expect(depositLink).not.toHaveAttribute("aria-current");
		await expect(
			page.getByRole("link", { name: "Past Due" }),
		).toHaveAttribute("aria-current", "page");
	});

	for (const { path, heading, exact } of [
		{ path: "/dashboards/executive", heading: "Executive Summary" },
		{ path: "/dashboards/deposits", heading: "Deposit Portfolio" },
		{ path: "/dashboards/past-due", heading: "Past Due", exact: true },
		{ path: "/dashboards/officer-branch", heading: "Officer / Branch Loans" },
	]) {
		test(`deep-link to ${path} renders correct heading`, async ({ page }) => {
			await page.goto(path);
			await expect(
				page.getByRole("heading", { name: heading, exact: exact ?? false }),
			).toBeVisible();
		});
	}

	test("deep-link to /intelligence renders the ask input", async ({ page }) => {
		await page.goto("/intelligence");
		await expect(page.getByRole("textbox")).toBeVisible();
	});

	test("/chat redirects to /intelligence", async ({ page }) => {
		await page.goto("/chat");
		await expect(page).toHaveURL("/intelligence");
	});
});
