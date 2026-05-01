import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
	);
});

test.describe("sidebar — mobile drawer", () => {
	test.use({ viewport: { width: 375, height: 812 } });

	test("hamburger button is present on narrow viewport", async ({ page }) => {
		await page.goto("/dashboards/executive");
		const hamburger = page.getByTestId("hamburger");
		await expect(hamburger).toBeAttached();
	});

	test("clicking hamburger opens the navigation drawer", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await page.getByTestId("hamburger").click({ force: true });
		await expect(
			page.getByRole("dialog", { name: "Navigation drawer" }),
		).toBeVisible();
	});

	test("nav links are visible inside drawer", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await page.getByTestId("hamburger").click({ force: true });
		const drawer = page.getByRole("dialog", { name: "Navigation drawer" });
		await expect(
			drawer.getByRole("link", { name: /Executive Summary/i }),
		).toBeVisible();
	});

	test("close button dismisses the drawer", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await page.getByTestId("hamburger").click({ force: true });
		await page
			.getByRole("dialog", { name: "Navigation drawer" })
			.getByRole("button", { name: "Close navigation" })
			.click();
		await expect(
			page.getByRole("dialog", { name: "Navigation drawer" }),
		).not.toBeVisible();
	});
});

test.describe("sidebar — desktop collapse", () => {
	test.use({ viewport: { width: 1366, height: 768 } });

	test("sidebar starts expanded", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await expect(page.getByText("Executive Summary").first()).toBeVisible();
	});

	test("collapse toggle hides labels", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await page.getByRole("button", { name: "Collapse sidebar" }).click();
		await expect(page.getByRole("link", { name: /Executive Summary/i })).toBeAttached();
	});
});
