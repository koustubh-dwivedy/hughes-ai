const SESSION_KEY = "hughes_session_id";

/**
 * Read or lazily generate a per-tab session id and persist it in
 * sessionStorage. The same id is reused for the lifetime of the tab,
 * which is what we want for cross-stack correlation: every fetch the
 * tab makes carries this id (X-Hughes-Session header), every
 * telemetry event is enriched with it, and the backend tags every log
 * record with it. Refreshing the tab keeps the session; closing the
 * tab issues a fresh one on next visit.
 */
export function getSessionId(): string {
	if (typeof window === "undefined" || !window.sessionStorage) {
		// SSR / non-browser environments: synthesize on the spot.
		return crypto.randomUUID();
	}
	const existing = window.sessionStorage.getItem(SESSION_KEY);
	if (existing) return existing;
	const fresh = crypto.randomUUID();
	window.sessionStorage.setItem(SESSION_KEY, fresh);
	return fresh;
}

export const SESSION_HEADER = "X-Hughes-Session";

export function _resetSessionForTesting(): void {
	if (typeof window !== "undefined" && window.sessionStorage) {
		window.sessionStorage.removeItem(SESSION_KEY);
	}
}
