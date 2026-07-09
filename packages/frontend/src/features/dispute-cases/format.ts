import type { TagVariant } from "../../ui/primitives/Tag";
import type { MatchResult, SignalStance } from "./types";

export const STANCE_LABEL: Record<SignalStance, string> = {
	supports: "Supports fraud",
	against: "Argues against",
	inconclusive: "Inconclusive",
};

export function stanceVariant(stance: SignalStance): TagVariant {
	switch (stance) {
		case "supports":
			return "danger";
		case "against":
			return "info";
		case "inconclusive":
			return "default";
	}
}

const USD = new Intl.NumberFormat("en-US", {
	style: "currency",
	currency: "USD",
	maximumFractionDigits: 0,
});

export function formatCurrency(value: number): string {
	return USD.format(value);
}

export function formatDate(iso: string): string {
	const d = new Date(iso);
	return Number.isNaN(d.getTime())
		? iso
		: d.toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
			});
}

/**
 * Whole calendar days from today until `iso`. Negative = past due. Used for
 * the queue's SLA countdown — fixed "now" isn't needed for a static mockup.
 */
export function daysUntil(iso: string): number {
	const target = new Date(iso).getTime();
	const now = Date.now();
	return Math.ceil((target - now) / 86_400_000);
}

/** Compact SLA label, e.g. "6d", "2d", "Due today", "—" (never "Overdue"). */
export function slaLabel(iso: string | null): string {
	if (!iso) return "—";
	const days = daysUntil(iso);
	// Past-due reads as "Due today" — the queue never shows an alarming "Overdue".
	if (days <= 0) return "Due today";
	return `${days}d`;
}

/** SLA urgency → Tag variant (danger when ≤2 days or overdue). */
export function slaVariant(iso: string | null): TagVariant {
	if (!iso) return "default";
	const days = daysUntil(iso);
	if (days <= 2) return "danger";
	if (days <= 5) return "warning";
	return "success";
}

export function matchVariant(result: MatchResult): TagVariant {
	switch (result) {
		case "Match":
			return "success";
		case "Mismatch":
			return "danger";
		case "Elevated":
			return "warning";
	}
}
