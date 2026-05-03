// Shared formatters + label maps for the per-dashboard headline writers.
// Pulled out of headlines.ts to keep that module under the 300-line cap.

export type HeadlineCalloutTone = "success" | "warn" | "info";
export type HeadlineTone = "success" | "warn" | "info" | "neutral";

export function fmtMoney(n: number): string {
	const abs = Math.abs(n);
	if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
	if (abs >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
	return `$${Math.round(n)}`;
}

export function fmtPct(n: number, digits = 1): string {
	return `${n.toFixed(digits)}%`;
}

export function dirArrow(n: number): "↑" | "↓" | "→" {
	if (n > 0) return "↑";
	if (n < 0) return "↓";
	return "→";
}

const PRODUCT_LABELS: Record<string, string> = {
	c_and_i: "Commercial Lending",
	cre: "Commercial Real Estate",
};

export function productLabel(slug: string): string {
	return PRODUCT_LABELS[slug] ?? slug;
}
