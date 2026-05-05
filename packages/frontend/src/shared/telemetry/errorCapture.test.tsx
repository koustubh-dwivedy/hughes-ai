import { render } from "@testing-library/react";
import * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ErrorBoundary from "../../ui/primitives/ErrorBoundary";
import * as telemetry from "./client";
import { installGlobalErrorHandlers, reportError } from "./errorCapture";

afterEach(() => {
	vi.restoreAllMocks();
	// emit() schedules a 5s setTimeout to flush the batch; without this
	// reset the timer keeps the test process alive after the assertions
	// have finished, ballooning total runtime.
	telemetry._resetBatchForTesting();
});

describe("reportError", () => {
	it("emits app.error with all the provided fields", () => {
		const spy = vi.spyOn(telemetry, "emit");
		reportError({
			message: "boom",
			stack: "at foo (bar.ts:1:1)",
			context: "manual",
		});
		expect(spy).toHaveBeenCalledWith({
			type: "app.error",
			message: "boom",
			stack: "at foo (bar.ts:1:1)",
			context: "manual",
		});
	});
});

describe("installGlobalErrorHandlers", () => {
	it("captures window.onerror as app.error with context=window_error", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const teardown = installGlobalErrorHandlers();
		try {
			window.dispatchEvent(
				new ErrorEvent("error", {
					message: "Boom!",
					error: new Error("Boom!"),
				}),
			);
			expect(spy).toHaveBeenCalledWith(
				expect.objectContaining({
					type: "app.error",
					message: "Boom!",
					context: "window_error",
				}),
			);
		} finally {
			teardown();
		}
	});

	it("captures unhandledrejection with context=unhandled_rejection", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const teardown = installGlobalErrorHandlers();
		try {
			const evt = new Event("unhandledrejection") as PromiseRejectionEvent;
			Object.defineProperty(evt, "reason", {
				value: new Error("rejected!"),
			});
			window.dispatchEvent(evt);
			expect(spy).toHaveBeenCalledWith(
				expect.objectContaining({
					type: "app.error",
					message: "rejected!",
					context: "unhandled_rejection",
				}),
			);
		} finally {
			teardown();
		}
	});

	it("teardown unsubscribes both listeners", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const teardown = installGlobalErrorHandlers();
		teardown();
		// Use a message-only ErrorEvent so vitest's own unhandled-error
		// catcher doesn't pick this up as a test failure.
		window.dispatchEvent(new ErrorEvent("error", { message: "ignored" }));
		expect(spy).not.toHaveBeenCalled();
	});
});

function Boom(): React.JSX.Element {
	throw new Error("render failure");
}

describe("ErrorBoundary integration", () => {
	it("emits app.error when a child component throws during render", () => {
		const spy = vi.spyOn(telemetry, "emit");
		// React logs the error via console.error during the test — silence it
		const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
		try {
			render(
				<ErrorBoundary>
					<Boom />
				</ErrorBoundary>,
			);
		} finally {
			consoleSpy.mockRestore();
		}
		expect(spy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "app.error",
				message: "render failure",
				context: "react_render",
			}),
		);
	});
});
