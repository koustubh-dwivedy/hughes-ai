import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { KBarProvider } from "kbar";
import { useEffect } from "react";
import { Provider as ReduxProvider } from "react-redux";
import CommandPalette, { defaultActions } from "../features/command-palette";
import { store } from "../shared/api/store";
import { initTelemetry } from "../shared/telemetry/client";
import { theme } from "../ui/theme";
import { cssVariablesResolver } from "../ui/tokens";

function TelemetryInit() {
	useEffect(() => initTelemetry(), []);
	return null;
}

export default function AppProviders({
	children,
}: { children: React.ReactNode }) {
	return (
		<ReduxProvider store={store}>
			<KBarProvider actions={defaultActions}>
				<MantineProvider
					theme={theme}
					cssVariablesResolver={cssVariablesResolver}
				>
					<TelemetryInit />
					<Notifications position="top-right" zIndex={1000} />
					<CommandPalette />
					{children}
				</MantineProvider>
			</KBarProvider>
		</ReduxProvider>
	);
}
