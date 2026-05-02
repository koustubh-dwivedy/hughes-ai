import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import AppProviders from "./app/AppProviders";
import { installGlobalErrorHandlers } from "./shared/telemetry/errorCapture";
import { initWebVitals } from "./shared/telemetry/webVitals";
import GlobalStyles from "./theme/GlobalStyles";
import ErrorBoundary from "./ui/primitives/ErrorBoundary";

installGlobalErrorHandlers();
initWebVitals();

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
