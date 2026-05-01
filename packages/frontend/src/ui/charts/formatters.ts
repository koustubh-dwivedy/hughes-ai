const MONTHS = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
] as const;

export function formatAxisCurrency(v: number): string {
	const abs = Math.abs(v);
	const sign = v < 0 ? "-" : "";
	if (abs >= 1_000_000_000) {
		return `${sign}$${(abs / 1_000_000_000).toFixed(1)}B`;
	}
	if (abs >= 1_000_000) {
		return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
	}
	if (abs >= 1_000) {
		return `${sign}$${(abs / 1_000).toFixed(1)}K`;
	}
	return `${sign}$${abs.toFixed(0)}`;
}

export function formatAxisPercent(v: number): string {
	return `${v.toFixed(1)}%`;
}

// Accepts "YYYY-MM" or "YYYY-MM-DD"
export function formatAxisDate(v: string): string {
	const parts = v.split("-");
	if (parts.length < 2) return v;
	const year = parts[0].slice(-2);
	const monthIdx = Number.parseInt(parts[1], 10) - 1;
	if (monthIdx < 0 || monthIdx > 11) return v;
	return `${MONTHS[monthIdx]} '${year}`;
}
