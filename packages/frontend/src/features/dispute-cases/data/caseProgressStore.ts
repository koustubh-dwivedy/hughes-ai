import { useSyncExternalStore } from "react";
import type { HumanAction } from "../ai/aiTypes";

/**
 * In-session progression state for dispute cases (mockup — no backend, resets
 * on reload). Lets a reviewer advance a case through its stages, record a
 * decision, and resolve it, with the result reflected in the case header and
 * the Case Queue for the rest of the session.
 */
export interface CaseProgress {
	stage: number;
	status: string;
	decision: HumanAction | null;
	resolved: boolean;
	outcome?: string;
}

const store = new Map<string, CaseProgress>();
let version = 0;
const listeners = new Set<() => void>();

function emit() {
	version += 1;
	for (const l of listeners) l();
}

function subscribe(listener: () => void): () => void {
	listeners.add(listener);
	return () => listeners.delete(listener);
}

/** Session override for a case, or undefined if it hasn't progressed yet. */
export function getOverride(id: string): CaseProgress | undefined {
	return store.get(id);
}

/** Seed a case's progress from its mock values (no emit — render-safe). */
function seed(id: string, stage: number, status: string): CaseProgress {
	const existing = store.get(id);
	if (existing) return existing;
	const fresh: CaseProgress = {
		stage,
		status,
		decision: null,
		resolved: false,
	};
	store.set(id, fresh);
	return fresh;
}

function update(id: string, patch: Partial<CaseProgress>) {
	const current = store.get(id);
	if (!current) return;
	// New object identity so the per-case snapshot changes.
	store.set(id, { ...current, ...patch });
	emit();
}

export function setStage(id: string, stage: number) {
	update(id, { stage });
}

export function setDecision(id: string, decision: HumanAction | null) {
	update(id, { decision });
}

export function resolveCase(id: string, outcome: string) {
	update(id, { resolved: true, status: "Resolved", outcome });
}

/** Test-only: clear all session progress (no emit — callers are tearing down). */
export function resetCaseProgress() {
	store.clear();
	version += 1;
}

/**
 * Reactive progress for one case. Seeds from the case's mock stage/status on
 * first use, then tracks the session store. The snapshot is the per-case
 * object, whose identity changes only when that case changes.
 */
export function useCaseProgress(
	id: string,
	initialStage: number,
	initialStatus: string,
): CaseProgress {
	seed(id, initialStage, initialStatus);
	return useSyncExternalStore(subscribe, () =>
		seed(id, initialStage, initialStatus),
	);
}

/**
 * Subscribe to any progress change (returns a version counter). Consumers read
 * `getOverride(id)` per case — used by the queue + KPIs to reflect resolution.
 */
export function useCaseProgressVersion(): number {
	return useSyncExternalStore(subscribe, () => version);
}
