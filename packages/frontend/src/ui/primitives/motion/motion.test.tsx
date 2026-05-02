import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
	getDuration,
	motionDurations,
	usePrefersReducedMotion,
} from "./usePrefersReducedMotion";

interface FakeMQL {
	matches: boolean;
	media: string;
	addEventListener: () => void;
	removeEventListener: () => void;
}

function stubMatchMedia(matches: boolean): FakeMQL {
	const fake: FakeMQL = {
		matches,
		media: "(prefers-reduced-motion: reduce)",
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
	};
	vi.stubGlobal(
		"matchMedia",
		vi.fn(() => fake) as unknown as typeof window.matchMedia,
	);
	Object.defineProperty(window, "matchMedia", {
		writable: true,
		configurable: true,
		value: vi.fn(() => fake),
	});
	return fake;
}

afterEach(() => {
	vi.unstubAllGlobals();
});

describe("usePrefersReducedMotion", () => {
	it("returns true when the OS reports prefers-reduced-motion: reduce", () => {
		stubMatchMedia(true);
		const { result } = renderHook(() => usePrefersReducedMotion());
		expect(result.current).toBe(true);
	});

	it("returns false when the OS allows motion", () => {
		stubMatchMedia(false);
		const { result } = renderHook(() => usePrefersReducedMotion());
		expect(result.current).toBe(false);
	});
});

describe("getDuration / motionDurations", () => {
	it("zeros every duration when reduced is true", () => {
		for (const key of Object.keys(motionDurations) as Array<
			keyof typeof motionDurations
		>) {
			expect(getDuration(key, true)).toBe(0);
		}
	});

	it("returns the canonical duration when reduced is false", () => {
		expect(getDuration("hoverLift", false)).toBe(80);
		expect(getDuration("routeFade", false)).toBe(150);
		expect(getDuration("countUp", false)).toBe(200);
		expect(getDuration("chartEntry", false)).toBe(350);
	});

	it("exports the four canonical durations specified by HUG-142", () => {
		expect(motionDurations).toEqual({
			hoverLift: 80,
			routeFade: 150,
			countUp: 200,
			chartEntry: 350,
		});
	});
});
