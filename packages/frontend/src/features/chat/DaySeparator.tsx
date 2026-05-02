import { colors, spacing, typography } from "../../theme/tokens";

interface Props {
	dateKey: string;
}

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	gap: spacing[3],
	margin: `${spacing[4]} 0`,
	color: colors.slate[400],
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	textTransform: "uppercase",
	letterSpacing: "0.06em",
};

const hrStyle: React.CSSProperties = {
	flex: 1,
	height: 1,
	border: 0,
	background: colors.slate[200],
	margin: 0,
};

export function formatDayLabel(dateKey: string, today = new Date()): string {
	const date = new Date(`${dateKey}T00:00:00`);
	const todayKey = today.toISOString().slice(0, 10);
	if (dateKey === todayKey) return "Today";
	const yesterday = new Date(today);
	yesterday.setDate(today.getDate() - 1);
	if (dateKey === yesterday.toISOString().slice(0, 10)) return "Yesterday";
	return date.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
		year: date.getFullYear() === today.getFullYear() ? undefined : "numeric",
	});
}

export default function DaySeparator({ dateKey }: Props) {
	const label = formatDayLabel(dateKey);
	return (
		<div style={wrapperStyle}>
			<hr aria-label={label} style={hrStyle} />
			<span aria-hidden="true">{label}</span>
		</div>
	);
}
