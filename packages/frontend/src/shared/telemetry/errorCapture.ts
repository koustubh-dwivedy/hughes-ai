import log from "../lib/logger";
import { emit } from "./client";

interface CaptureInput {
	message: string;
	stack?: string;
	context?: string;
}

/**
 * Emit a single app.error telemetry event. The shared `enrich()` in
 * `client.ts` already attaches `route`, `session_id`, `ts`, viewport
 * dims, so we only need message + stack + context here. Errors are
 * also forwarded to the structured logger so they show up in dev
 * console.
 */
export function reportError({ message, stack, context }: CaptureInput): void {
	emit({
		type: "app.error",
		message,
		stack,
		context,
	});
	log.error({ err: message, stack, context }, "app_error");
}

function onError(event: ErrorEvent): void {
	reportError({
		message: event.message,
		stack: event.error instanceof Error ? event.error.stack : undefined,
		context: "window_error",
	});
}

function onRejection(event: PromiseRejectionEvent): void {
	const reason = event.reason;
	const message = reason instanceof Error ? reason.message : String(reason);
	const stack = reason instanceof Error ? reason.stack : undefined;
	reportError({ message, stack, context: "unhandled_rejection" });
}

/**
 * Install window-level handlers for synchronous errors and unhandled
 * promise rejections. Returns an unsubscribe function so tests can
 * tear down between cases.
 */
export function installGlobalErrorHandlers(): () => void {
	window.addEventListener("error", onError);
	window.addEventListener("unhandledrejection", onRejection);
	return () => {
		window.removeEventListener("error", onError);
		window.removeEventListener("unhandledrejection", onRejection);
	};
}
