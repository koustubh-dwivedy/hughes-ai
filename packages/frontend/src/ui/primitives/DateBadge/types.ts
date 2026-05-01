export interface DateBadgeProps {
	asOfDate: string; // ISO date string, e.g. "2026-04-30"
	refreshedAt?: string; // ISO datetime string
	tooltip?: string; // extra context on hover
}
