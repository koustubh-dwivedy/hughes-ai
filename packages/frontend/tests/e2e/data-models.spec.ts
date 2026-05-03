import { expect, test } from "@playwright/test";

const GRAPH_FIXTURE = {
	audit_id: "e2e-aid",
	generated_at: "2026-05-04T00:00:00Z",
	nodes: [
		{
			id: "source.hughes_ai.raw.booked_loans",
			name: "booked_loans",
			kind: "source",
			layer: "Sources",
			materialization: null,
			description: "Raw booked loans",
			nl_query_count_30d: 0,
		},
		{
			id: "model.hughes_ai.fct_loans_monthly",
			name: "fct_loans_monthly",
			kind: "mart",
			layer: "Marts",
			materialization: "table",
			description: "Monthly loan rollup.",
			nl_query_count_30d: 3,
		},
		{
			id: "dashboard.executive",
			name: "Executive Summary",
			kind: "dashboard",
			layer: "Dashboards",
			materialization: null,
			description: "Dashboard at /dashboards/executive",
			nl_query_count_30d: 0,
		},
	],
	edges: [
		{
			source: "source.hughes_ai.raw.booked_loans",
			target: "model.hughes_ai.fct_loans_monthly",
		},
		{
			source: "model.hughes_ai.fct_loans_monthly",
			target: "dashboard.executive",
		},
	],
};

const NODE_FIXTURE = {
	...GRAPH_FIXTURE.nodes[1],
	columns: [
		{ name: "as_of_month", type: "DATE", description: "Month start." },
		{ name: "total_balance", type: "NUMERIC", description: "Sum of balances." },
	],
	parents: ["source.hughes_ai.raw.booked_loans"],
	children: ["dashboard.executive"],
	dashboards: [
		{
			id: "dashboard.executive",
			name: "Executive Summary",
			route: "/dashboards/executive",
		},
	],
	sql: "SELECT 1",
	file_path: "models/marts/fct_loans_monthly.sql",
	last_run_at: null,
};

test.beforeEach(async ({ page }) => {
	await page.route("**/api/data-model/graph", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(GRAPH_FIXTURE),
		}),
	);
	await page.route("**/api/data-model/nodes/**", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(NODE_FIXTURE),
		}),
	);
	// Other API calls used by the layout (sidebar, dashboards, etc.) get a noop.
	await page.route("**/api/dashboards/**", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
	);
	await page.route("**/api/trust", (route) =>
		route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
	);
});

test.describe("Data Models page", () => {
	test("renders filter bar and DAG canvas", async ({ page }) => {
		await page.goto("/data/models");
		await expect(
			page.getByRole("toolbar", { name: "Data model filters" }),
		).toBeVisible();
		await expect(page.locator(".react-flow")).toBeVisible();
	});

	test("sidebar link navigates to Data Models", async ({ page }) => {
		await page.goto("/dashboards/executive");
		await page.getByRole("link", { name: "Data Models" }).click();
		await expect(page).toHaveURL(/\/data\/models$/);
		await expect(
			page.getByRole("toolbar", { name: "Data model filters" }),
		).toBeVisible();
	});

	test("clicking a node opens the detail drawer with columns and dashboards", async ({
		page,
	}) => {
		await page.goto("/data/models");
		// Wait for nodes to render in react-flow.
		await expect(page.getByText("fct_loans_monthly").first()).toBeVisible();
		await page.getByText("fct_loans_monthly").first().click();

		const drawer = page.getByRole("dialog");
		await expect(drawer).toBeVisible();
		await expect(drawer).toContainText("Executive Summary");
		await expect(drawer).toContainText("as_of_month");
		await expect(drawer).toContainText("Monthly loan rollup.");
	});

	test("dashboard chip in drawer links to the dashboard route", async ({
		page,
	}) => {
		await page.goto("/data/models");
		await page.getByText("fct_loans_monthly").first().click();
		const drawer = page.getByRole("dialog");
		await drawer.getByRole("link", { name: "Executive Summary" }).click();
		await expect(page).toHaveURL(/\/dashboards\/executive$/);
	});

	test("toggling Sources layer hides source nodes", async ({ page }) => {
		await page.goto("/data/models");
		await expect(page.getByText("booked_loans").first()).toBeVisible();
		const toolbar = page.getByRole("toolbar", { name: "Data model filters" });
		await toolbar
			.getByRole("button", { name: "Sources", pressed: true })
			.click();
		await expect(page.getByText("booked_loans")).toHaveCount(0);
	});
});
