import { afterEach, describe, expect, it } from "vitest";
import { USER_HEADER, _resetUserForTesting, getUserId } from "../user";

describe("getUserId — durable identity (HUG-205)", () => {
	afterEach(() => {
		_resetUserForTesting();
	});

	it("generates a UUID on first call and persists it in localStorage", () => {
		_resetUserForTesting();
		const first = getUserId();
		expect(first).toMatch(
			/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
		);
		expect(window.localStorage.getItem("hughes_user_id")).toBe(first);
	});

	it("returns the same UUID across subsequent calls (durability)", () => {
		_resetUserForTesting();
		const a = getUserId();
		const b = getUserId();
		const c = getUserId();
		expect(a).toBe(b);
		expect(b).toBe(c);
	});

	it("does NOT clear when sessionStorage clears (sessionStorage is unrelated)", () => {
		_resetUserForTesting();
		const original = getUserId();
		// Wipe sessionStorage as a tab-close would. localStorage must
		// survive — that's the whole point.
		window.sessionStorage.clear();
		expect(getUserId()).toBe(original);
	});

	it("exports the X-Hughes-User header constant", () => {
		expect(USER_HEADER).toBe("X-Hughes-User");
	});
});
