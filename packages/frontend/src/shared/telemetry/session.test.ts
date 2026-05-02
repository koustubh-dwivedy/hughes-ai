import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	SESSION_HEADER,
	_resetSessionForTesting,
	getSessionId,
} from "./session";

beforeEach(() => {
	_resetSessionForTesting();
});

afterEach(() => {
	vi.restoreAllMocks();
	_resetSessionForTesting();
});

describe("getSessionId", () => {
	it("generates a UUID on first call and persists it in sessionStorage", () => {
		const id = getSessionId();
		expect(id).toMatch(/^[0-9a-f-]{36}$/);
		expect(window.sessionStorage.getItem("hughes_session_id")).toBe(id);
	});

	it("returns the same id on subsequent calls within the tab", () => {
		const a = getSessionId();
		const b = getSessionId();
		expect(a).toBe(b);
	});

	it("rehydrates a previously-persisted id from sessionStorage", () => {
		window.sessionStorage.setItem("hughes_session_id", "fixed-id-123");
		expect(getSessionId()).toBe("fixed-id-123");
	});
});

describe("SESSION_HEADER constant", () => {
	it("matches the cross-stack contract X-Hughes-Session", () => {
		expect(SESSION_HEADER).toBe("X-Hughes-Session");
	});
});
