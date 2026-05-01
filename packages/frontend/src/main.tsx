import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import AppProviders from "./app/AppProviders";
import log from "./shared/lib/logger";
import GlobalStyles from "./theme/GlobalStyles";
import ErrorBoundary from "./ui/primitives/ErrorBoundary";

window.addEventListener("error", (event) => {
	log.error(
		{ err: event.message, filename: event.filename, lineno: event.lineno },
		"global_error",
	);
});

window.addEventListener("unhandledrejection", (event) => {
	const message =
		event.reason instanceof Error ? event.reason.message : String(event.reason);
	log.error({ err: message }, "unhandled_rejection");
});

const rootEl = document.getElementById("root");
if (rootEl === null) throw new Error("Root element not found");
createRoot(rootEl).render(
	<StrictMode>
		<ErrorBoundary>
			<AppProviders>
				<GlobalStyles />
				<App />
			</AppProviders>
		</ErrorBoundary>
	</StrictMode>,
);
