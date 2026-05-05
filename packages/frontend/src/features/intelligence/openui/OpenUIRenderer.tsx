/**
 * OpenUIRenderer — wraps `@openuidev/react-lang`'s `<Renderer>` with an
 * error boundary that surfaces a clean fallback if the parser blows up.
 *
 * Phase A (HUG-178): production behavior is unchanged — the agent does
 * not yet emit `openui_dsl`, so this component never renders in
 * production today. It's wired ahead of Phase B's agent prompt
 * injection so the rendering stack is in place when the agent flips on.
 *
 * The OpenUI parser is permissive — invalid DSL renders what it can.
 * The error boundary catches *runtime* renderer crashes (e.g., a
 * registered component throwing), not parse-level issues.
 */

import { Renderer } from "@openuidev/react-lang";
import * as React from "react";
import { library } from "./library";

interface Props {
	/** Raw OpenUI Lang DSL string emitted by the agent. */
	dsl: string;
	/**
	 * Optional fallback rendered when the OpenUI tree throws at runtime
	 * (parse errors are tolerated by the parser itself; this only fires
	 * on uncaught exceptions inside a registered component).
	 */
	fallback?: React.ReactNode;
}

interface State {
	hasError: boolean;
}

/** Error boundary scoped to a single OpenUI tree. */
class OpenUIErrorBoundary extends React.Component<
	React.PropsWithChildren<{ fallback: React.ReactNode }>,
	State
> {
	state: State = { hasError: false };

	static getDerivedStateFromError(): State {
		return { hasError: true };
	}

	componentDidCatch(error: Error): void {
		// Surface to console so a misbehaving DSL is visible in dev. The
		// existing telemetry pipeline (errorCapture / reportError) is the
		// production destination; wiring it up is HUG-179 follow-on work.
		// biome-ignore lint/suspicious/noConsole: dev-only diagnostic until telemetry is wired.
		console.error("OpenUIRenderer crashed:", error);
	}

	render(): React.ReactNode {
		if (this.state.hasError) {
			return this.props.fallback;
		}
		return this.props.children;
	}
}

const DefaultFallback: React.FC = () => (
	<div role="alert" aria-live="polite">
		Could not render the assistant&apos;s structured response.
	</div>
);

const OpenUIRenderer: React.FC<Props> = ({ dsl, fallback }) => {
	return (
		<OpenUIErrorBoundary fallback={fallback ?? <DefaultFallback />}>
			<Renderer response={dsl} library={library} />
		</OpenUIErrorBoundary>
	);
};

export default OpenUIRenderer;
