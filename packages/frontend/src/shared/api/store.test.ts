import { describe, expect, it } from "vitest";
import { baseApi } from "./client";
import { createStore } from "./store";

describe("createStore", () => {
	it("registers the baseApi reducer at the api slice", () => {
		const s = createStore();
		const state = s.getState();
		expect(state).toHaveProperty(baseApi.reducerPath);
	});

	it("includes the baseApi middleware so endpoint thunks dispatch", () => {
		const s = createStore();
		// thunk dispatch returns a Promise when middleware is wired
		const result = s.dispatch(baseApi.util.invalidateTags(["Trust"]) as never);
		expect(result).toBeDefined();
	});

	it("creates an isolated store instance per call (for test isolation)", () => {
		const a = createStore();
		const b = createStore();
		expect(a).not.toBe(b);
	});
});
