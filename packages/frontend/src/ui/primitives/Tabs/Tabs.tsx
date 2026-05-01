import { Tabs as MantineTabs } from "@mantine/core";
import type { TabsProps } from "@mantine/core";

// Re-export with animated underline default
export default function Tabs({ children, ...props }: TabsProps) {
	return (
		<MantineTabs variant="default" keepMounted={false} {...props}>
			{children}
		</MantineTabs>
	);
}

// Also re-export sub-components so callers can do:
// import Tabs from "ui/primitives/Tabs"
// <Tabs><Tabs.List>...</Tabs.List><Tabs.Panel>...</Tabs.Panel></Tabs>
export const TabsList = MantineTabs.List;
export const TabsTab = MantineTabs.Tab;
export const TabsPanel = MantineTabs.Panel;
