import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Tabs, { TabsList, TabsPanel, TabsTab } from "./Tabs";

function withMantine(ui: React.ReactElement) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("Tabs", () => {
	it("renders tab list with 2 tabs", () => {
		withMantine(
			<Tabs defaultValue="tab1">
				<TabsList>
					<TabsTab value="tab1">Tab One</TabsTab>
					<TabsTab value="tab2">Tab Two</TabsTab>
				</TabsList>
				<TabsPanel value="tab1">Panel One</TabsPanel>
				<TabsPanel value="tab2">Panel Two</TabsPanel>
			</Tabs>,
		);
		expect(screen.getByText("Tab One")).toBeInTheDocument();
		expect(screen.getByText("Tab Two")).toBeInTheDocument();
	});

	it("clicking a tab changes the active panel", async () => {
		const user = userEvent.setup();
		const onChange = vi.fn();
		withMantine(
			<Tabs defaultValue="tab1" onChange={onChange}>
				<TabsList>
					<TabsTab value="tab1">Tab One</TabsTab>
					<TabsTab value="tab2">Tab Two</TabsTab>
				</TabsList>
				<TabsPanel value="tab1">Panel One</TabsPanel>
				<TabsPanel value="tab2">Panel Two</TabsPanel>
			</Tabs>,
		);
		await user.click(screen.getByText("Tab Two"));
		expect(onChange).toHaveBeenCalledWith("tab2");
	});

	it("keyboard ArrowRight moves focus to next tab", async () => {
		const user = userEvent.setup();
		withMantine(
			<Tabs defaultValue="tab1">
				<TabsList>
					<TabsTab value="tab1">Tab One</TabsTab>
					<TabsTab value="tab2">Tab Two</TabsTab>
				</TabsList>
				<TabsPanel value="tab1">Panel One</TabsPanel>
				<TabsPanel value="tab2">Panel Two</TabsPanel>
			</Tabs>,
		);
		const firstTab = screen.getByRole("tab", { name: "Tab One" });
		firstTab.focus();
		await user.keyboard("{ArrowRight}");
		expect(document.activeElement).toBe(
			screen.getByRole("tab", { name: "Tab Two" }),
		);
	});

	it("keepMounted={false} means inactive panels are not in DOM", () => {
		withMantine(
			<Tabs defaultValue="tab1">
				<TabsList>
					<TabsTab value="tab1">Tab One</TabsTab>
					<TabsTab value="tab2">Tab Two</TabsTab>
				</TabsList>
				<TabsPanel value="tab1">Panel One</TabsPanel>
				<TabsPanel value="tab2">Panel Two Only</TabsPanel>
			</Tabs>,
		);
		expect(screen.getByText("Panel One")).toBeInTheDocument();
		expect(screen.queryByText("Panel Two Only")).not.toBeInTheDocument();
	});
});
