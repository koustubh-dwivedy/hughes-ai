import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { KBarProvider } from "kbar";
import CommandPalette, { defaultActions } from "../features/command-palette";
import { theme } from "../ui/theme";
import { cssVariablesResolver } from "../ui/tokens";

export default function AppProviders({
	children,
}: { children: React.ReactNode }) {
	return (
		<KBarProvider actions={defaultActions}>
			<MantineProvider
				theme={theme}
				cssVariablesResolver={cssVariablesResolver}
			>
				<Notifications position="top-right" zIndex={1000} />
				<CommandPalette />
				{children}
			</MantineProvider>
		</KBarProvider>
	);
}
