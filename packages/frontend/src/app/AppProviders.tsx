import "@mantine/core/styles.css";
import { MantineProvider } from "@mantine/core";
import { theme } from "../ui/theme";

export default function AppProviders({
	children,
}: { children: React.ReactNode }) {
	return <MantineProvider theme={theme}>{children}</MantineProvider>;
}
