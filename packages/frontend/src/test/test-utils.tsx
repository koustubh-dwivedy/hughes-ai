import { MantineProvider } from "@mantine/core";
import { type RenderOptions, render } from "@testing-library/react";
import { KBarProvider } from "kbar";
import { theme } from "../ui/theme";

function Wrapper({ children }: { children: React.ReactNode }) {
	return (
		<KBarProvider actions={[]}>
			<MantineProvider theme={theme}>{children}</MantineProvider>
		</KBarProvider>
	);
}

export function renderWithProviders(
	ui: React.ReactElement,
	options?: Omit<RenderOptions, "wrapper">,
) {
	return render(ui, { wrapper: Wrapper, ...options });
}

export * from "@testing-library/react";
