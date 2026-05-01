import "@mantine/core/styles.css";
import { MantineProvider } from "@mantine/core";
import { theme } from "../ui/theme";
import { cssVariablesResolver } from "../ui/tokens";

export default function AppProviders({
	children,
}: { children: React.ReactNode }) {
	return (
		<MantineProvider theme={theme} cssVariablesResolver={cssVariablesResolver}>
			{children}
		</MantineProvider>
	);
}
