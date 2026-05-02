import log from "../lib/logger";
import type { TelemetryEvent } from "./events";
import { getSessionId } from "./session";

const SESSION_ID = getSessionId();
const BATCH_MAX = 20;
const FLUSH_INTERVAL_MS = 5_000;

type EnrichedEvent = TelemetryEvent & {
	session_id: string;
	ts: number;
	route: string;
	viewport_w: number;
	viewport_h: number;
};

const buffer: EnrichedEvent[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

function enrich(event: TelemetryEvent): EnrichedEvent {
	return {
		...event,
		session_id: SESSION_ID,
		ts: Date.now(),
		route: window.location.pathname,
		viewport_w: window.innerWidth,
		viewport_h: window.innerHeight,
	};
}

async function flushHttp(events: EnrichedEvent[]): Promise<void> {
	try {
		await fetch("/api/log", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ events }),
		});
	} catch (err: unknown) {
		log.warn(
			{ err: err instanceof Error ? err.message : String(err) },
			"telemetry_flush_failed",
		);
	}
}

function flushBeacon(events: EnrichedEvent[]): void {
	navigator.sendBeacon("/api/log", JSON.stringify({ events }));
}

function scheduleFlush(): void {
	if (flushTimer !== null) return;
	flushTimer = setTimeout(() => {
		flushTimer = null;
		const batch = buffer.splice(0);
		if (batch.length > 0) {
			flushHttp(batch);
		}
	}, FLUSH_INTERVAL_MS);
}

export function emit(event: TelemetryEvent): void {
	buffer.push(enrich(event));
	if (buffer.length >= BATCH_MAX) {
		if (flushTimer !== null) {
			clearTimeout(flushTimer);
			flushTimer = null;
		}
		const batch = buffer.splice(0);
		flushHttp(batch);
	} else {
		scheduleFlush();
	}
}

export function initTelemetry(): () => void {
	function onUnload(): void {
		const batch = buffer.splice(0);
		if (batch.length > 0) {
			flushBeacon(batch);
		}
	}
	function onVisibility(): void {
		if (document.visibilityState === "hidden") onUnload();
	}
	document.addEventListener("visibilitychange", onVisibility);
	return () => {
		document.removeEventListener("visibilitychange", onVisibility);
	};
}

export { SESSION_ID };

export function _resetBatchForTesting(): void {
	buffer.splice(0);
	if (flushTimer !== null) {
		clearTimeout(flushTimer);
		flushTimer = null;
	}
}
