/**
 * Durable per-browser identity for thread ownership (HUG-205).
 *
 * Distinct from `getSessionId()`:
 *   - session_id lives in sessionStorage → ephemeral, per-tab, dies on
 *     tab close. Used purely for telemetry / log correlation.
 *   - user_id lives in localStorage → durable, per-browser, survives
 *     tab close + browser restart + days of dormancy. Used to filter
 *     `GET /threads` so chat history follows the user across visits.
 *
 * Same anonymous-UUID pattern, different storage backing. No
 * authentication; `localStorage` IS the identity.
 */

const USER_KEY = "hughes_user_id";

export function getUserId(): string {
	if (typeof window === "undefined" || !window.localStorage) {
		// SSR / non-browser environments: synthesize on the spot. Won't
		// persist, but prevents crashes during Node-side rendering.
		return crypto.randomUUID();
	}
	const existing = window.localStorage.getItem(USER_KEY);
	if (existing) return existing;
	const fresh = crypto.randomUUID();
	window.localStorage.setItem(USER_KEY, fresh);
	return fresh;
}

export const USER_HEADER = "X-Hughes-User";

export function _resetUserForTesting(): void {
	if (typeof window !== "undefined" && window.localStorage) {
		window.localStorage.removeItem(USER_KEY);
	}
}
