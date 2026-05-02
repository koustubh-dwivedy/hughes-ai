import { render } from "@testing-library/react";
import { KBarProvider } from "kbar";
import { describe, expect, it } from "vitest";
import CommandPalette from "./CommandPalette";
import { defaultActions } from "./actions";

describe("defaultActions", () => {
	it("includes all four dashboard navigation actions", () => {
		const ids = defaultActions.map((a) => a.id);
		expect(ids).toContain("nav-executive");
		expect(ids).toContain("nav-deposits");
		expect(ids).toContain("nav-past-due");
		expect(ids).toContain("nav-officers");
	});

	it("includes tools actions", () => {
		const ids = defaultActions.map((a) => a.id);
		expect(ids).toContain("nav-chat");
		expect(ids).toContain("help");
	});

	it("all actions have id, name, and perform function", () => {
		for (const action of defaultActions) {
			expect(action.id).toBeTruthy();
			expect(action.name).toBeTruthy();
			expect(typeof action.perform).toBe("function");
		}
	});

	it("dashboard actions have Dashboards section", () => {
		const dashboardIds = [
			"nav-executive",
			"nav-deposits",
			"nav-past-due",
			"nav-officers",
		];
		for (const id of dashboardIds) {
			const action = defaultActions.find((a) => a.id === id);
			expect(action?.section).toBe("Dashboards");
		}
	});
});

describe("CommandPalette", () => {
	it("renders without throwing when mounted inside KBarProvider", () => {
		expect(() =>
			render(
				<KBarProvider actions={[]}>
					<CommandPalette />
				</KBarProvider>,
			),
		).not.toThrow();
	});
});
