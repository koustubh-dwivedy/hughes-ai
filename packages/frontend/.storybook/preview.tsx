import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@mantine/core/styles.css";
import "./loki.css";
import { MantineProvider } from "@mantine/core";
import type { Preview } from "@storybook/react";
import { theme } from "../src/ui/theme";
import { cssVariablesResolver } from "../src/ui/tokens";

const preview: Preview = {
	decorators: [
		(Story) => (
			<MantineProvider
				theme={theme}
				cssVariablesResolver={cssVariablesResolver}
			>
				<Story />
			</MantineProvider>
		),
	],
	parameters: {
		layout: "centered",
	},
};

export default preview;
