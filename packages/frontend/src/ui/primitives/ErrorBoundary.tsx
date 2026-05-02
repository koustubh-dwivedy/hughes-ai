import { Component, type ErrorInfo, type ReactNode } from "react";
import { reportError } from "../../shared/telemetry/errorCapture";

interface Props {
	children: ReactNode;
}

interface State {
	hasError: boolean;
	message: string;
}

export default class ErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = { hasError: false, message: "" };
	}

	static getDerivedStateFromError(error: Error): State {
		return { hasError: true, message: error.message };
	}

	componentDidCatch(error: Error, info: ErrorInfo): void {
		reportError({
			message: error.message,
			stack: error.stack ?? info.componentStack ?? undefined,
			context: "react_render",
		});
	}

	render(): ReactNode {
		if (this.state.hasError) {
			return (
				<div role="alert" style={{ padding: "2rem", color: "red" }}>
					<h2>Something went wrong</h2>
					<p>{this.state.message}</p>
					<button
						type="button"
						onClick={() => this.setState({ hasError: false, message: "" })}
					>
						Try again
					</button>
				</div>
			);
		}
		return this.props.children;
	}
}
