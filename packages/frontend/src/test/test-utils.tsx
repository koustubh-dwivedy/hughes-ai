import { MantineProvider } from "@mantine/core";
import { type RenderOptions, render } from "@testing-library/react";
import { KBarProvider } from "kbar";
import { Provider as ReduxProvider } from "react-redux";
import { createStore } from "../shared/api/store";
import { theme } from "../ui/theme";

function Wrapper({ children }: { children: React.ReactNode }) {
	const store = createStore();
	return (
		<ReduxProvider store={store}>
			<KBarProvider actions={[]}>
				<MantineProvider theme={theme}>{children}</MantineProvider>
			</KBarProvider>
		</ReduxProvider>
	);
}

export function renderWithProviders(
	ui: React.ReactElement,
	options?: Omit<RenderOptions, "wrapper">,
) {
	return render(ui, { wrapper: Wrapper, ...options });
}

export * from "@testing-library/react";
