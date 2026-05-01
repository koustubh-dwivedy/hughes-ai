/**
 * Format a number as a currency string.
 * $42.5M for ≥1,000,000; $142.5K for ≥1,000; $142 otherwise.
 * Handles negatives correctly: -$1.2M not $-1.2M.
 */
export function formatCurrency(n: number): string {
	const sign = n < 0 ? "-" : "";
	const abs = Math.abs(n);
	if (abs >= 1_000_000) {
		const m = abs / 1_000_000;
		return `${sign}$${Number.parseFloat(m.toFixed(1))}M`;
	}
	if (abs >= 1_000) {
		const k = abs / 1_000;
		return `${sign}$${Number.parseFloat(k.toFixed(1))}K`;
	}
	return `${sign}$${Math.round(abs)}`;
}

/**
 * Format a ratio as a percentage string.
 * 0.032 → "3.2%", 0.913 → "91.3%"
 */
export function formatPercent(n: number, decimals = 1): string {
	return `${(n * 100).toFixed(decimals)}%`;
}

/**
 * Format a percentage-point delta with an arrow indicator.
 * positive: "↑ 4.2%", negative: "↓ 1.8%", zero: "—"
 * n is already a percentage point value (not a ratio).
 */
export function formatDelta(n: number, decimals = 1): string {
	if (n === 0) return "—";
	if (n > 0) return `↑ ${n.toFixed(decimals)}%`;
	return `↓ ${Math.abs(n).toFixed(decimals)}%`;
}
