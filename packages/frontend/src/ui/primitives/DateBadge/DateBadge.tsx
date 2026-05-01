import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { DateBadgeProps } from "./types";

function formatAsOf(isoDate: string): string {
	const [year, month, day] = isoDate.split("-").map(Number);
	const date = new Date(year, month - 1, day);
	return new Intl.DateTimeFormat("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
	}).format(date);
}

function formatRelative(isoDatetime: string): string {
	const refreshed = new Date(isoDatetime);
	const now = Date.now();
	const diffMs = now - refreshed.getTime();
	const diffSec = Math.floor(diffMs / 1000);

	if (diffSec < 60) {
		return "just now";
	}

	const diffMin = Math.floor(diffSec / 60);
	if (diffMin < 60) {
		const rtf = new Intl.RelativeTimeFormat("en-US", { numeric: "always" });
		return rtf
			.format(-diffMin, "minute")
			.replace(" minutes ago", " min ago")
			.replace(" minute ago", " min ago");
	}

	const diffHr = Math.floor(diffMin / 60);
	const rtf = new Intl.RelativeTimeFormat("en-US", { numeric: "always" });
	return rtf
		.format(-diffHr, "hour")
		.replace(" hours ago", " hr ago")
		.replace(" hour ago", " hr ago");
}

export default function DateBadge({
	asOfDate,
	refreshedAt,
	tooltip,
}: DateBadgeProps) {
	const asOfLabel = formatAsOf(asOfDate);
	const refreshLabel = refreshedAt ? formatRelative(refreshedAt) : null;

	return (
		<output
			title={tooltip}
			style={{
				display: "inline-flex",
				alignItems: "center",
				gap: spacing[1],
				fontSize: typography.size.xs,
				color: colors.slate[500],
				border: `1px solid ${colors.slate[200]}`,
				borderRadius: radii.md,
				padding: `${spacing[1]} ${spacing[2]}`,
				whiteSpace: "nowrap",
			}}
		>
			{`As of ${asOfLabel}`}
			{refreshLabel && ` · refreshed ${refreshLabel}`}
		</output>
	);
}
