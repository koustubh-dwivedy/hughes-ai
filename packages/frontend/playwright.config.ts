import { defineConfig, devices } from "@playwright/test";

// Smoke specs picked for cross-browser runs: navigation + the four
// dashboard-render specs. Keeps Firefox/WebKit fast in CI while still
// catching engine-specific regressions in the most-trafficked paths.
const SMOKE_SPECS = [
	"navigation.spec.ts",
	"dashboards-executive.spec.ts",
	"dashboards-deposits.spec.ts",
	"dashboards-past-due.spec.ts",
	"dashboards-officer-branch.spec.ts",
];

export default defineConfig({
	testDir: "./tests/e2e",
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	reporter: process.env.CI ? "github" : "list",
	globalSetup: "./tests/e2e/global-setup.ts",
	use: {
		baseURL: "http://localhost:5173",
		trace: "on-first-retry",
		screenshot: "only-on-failure",
	},
	projects: [
		{ name: "chromium", use: { ...devices["Desktop Chrome"] } },
		{
			name: "firefox-smoke",
			testMatch: SMOKE_SPECS,
			use: { ...devices["Desktop Firefox"] },
		},
		{
			name: "webkit-smoke",
			testMatch: SMOKE_SPECS,
			use: { ...devices["Desktop Safari"] },
		},
	],
	webServer: {
		command: "node_modules/.bin/vite",
		url: "http://localhost:5173",
		reuseExistingServer: !process.env.CI,
		timeout: 30_000,
	},
});
