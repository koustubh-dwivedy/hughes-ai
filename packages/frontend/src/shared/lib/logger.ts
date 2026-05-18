import pino from "pino";
import { baseUrl as API_BASE } from "../api/client";

const LEVEL_MAP: Record<number, "info" | "warn" | "error"> = {
	30: "info",
	40: "warn",
	50: "error",
	60: "error",
};

// HUG-260: use the same API base as RTK Query; the prod build resolves to
// api.tryhughes.com (cross-origin from app.tryhughes.com).
const LOG_URL = `${API_BASE}/log`;

function shipLog(o: object): void {
	const obj = o as Record<string, unknown>;
	const level = LEVEL_MAP[(obj.level as number) ?? 30] ?? "info";
	const { level: _l, time: _t, msg, ...context } = obj;
	const payload = JSON.stringify({
		level,
		message: String(msg ?? ""),
		context,
	});
	// sendBeacon survives page-unload; fetch with keepalive as fallback
	if (typeof navigator !== "undefined" && navigator.sendBeacon) {
		navigator.sendBeacon(
			LOG_URL,
			new Blob([payload], { type: "application/json" }),
		);
	} else {
		fetch(LOG_URL, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: payload,
			keepalive: true,
		}).catch((_err: unknown) => {
			// fire-and-forget: never block the UI on log delivery
		});
	}
}

const log = pino({
	browser: { asObject: true, write: shipLog },
	level: "info",
});

export default log;
