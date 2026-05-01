import type React from "react";
import { useState } from "react";
import { Line, LineChart } from "recharts";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { KpiTileProps } from "./types";

const POSITIVE_COLOR = "#16a34a";
const NEGATIVE_COLOR = "#dc2626";
const NEUTRAL_COLOR = colors.slate[400];

function deltaColor(deltaPositive: boolean | undefined): string {
	if (deltaPositive === true) return POSITIVE_COLOR;
	if (deltaPositive === false) return NEGATIVE_COLOR;
	return NEUTRAL_COLOR;
}

interface HeaderRowProps {
	label: string;
	icon?: React.ReactNode;
	infoTooltip?: string;
}

function HeaderRow({ label, icon, infoTooltip }: HeaderRowProps) {
	return (
		<div style={{ display: "flex", alignItems: "center", gap: spacing[1] }}>
			{icon !== undefined && (
				<span
					style={{ fontSize: 16, color: colors.indigo[500], lineHeight: 1 }}
				>
					{icon}
				</span>
			)}
			<span
				style={{
					fontSize: typography.size.xs,
					fontWeight: typography.weight.medium,
					color: colors.slate[500],
					textTransform: "uppercase",
					letterSpacing: "0.05em",
				}}
			>
				{label}
			</span>
			{infoTooltip !== undefined && (
				<button
					type="button"
					title={infoTooltip}
					aria-label={infoTooltip}
					style={{
						background: "none",
						border: "none",
						padding: 0,
						marginLeft: spacing[1],
						cursor: "help",
						color: colors.slate[400],
						fontSize: typography.size.xs,
						lineHeight: 1,
					}}
				>
					ⓘ
				</button>
			)}
		</div>
	);
}

export default function KpiTile({
	label,
	value,
	delta,
	deltaPositive,
	sparkline,
	icon,
	infoTooltip,
	onClick,
	loading = false,
}: KpiTileProps) {
	const [hovered, setHovered] = useState(false);

	if (loading) {
		return (
			<output
				aria-label="loading"
				style={{
					display: "block",
					width: 180,
					height: 90,
					backgroundColor: colors.slate[100],
					borderRadius: radii.lg,
				}}
			/>
		);
	}

	const isClickable = onClick !== undefined;

	function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
		if (e.key === "Enter" && onClick) {
			onClick();
		}
	}

	const cardStyle: React.CSSProperties = {
		display: "inline-flex",
		flexDirection: "column",
		gap: spacing[1],
		padding: spacing[4],
		border: `1px solid ${colors.slate[200]}`,
		borderRadius: radii.lg,
		backgroundColor: colors.white,
		minWidth: 160,
		transition: "box-shadow 150ms ease",
		boxShadow: hovered ? "0 4px 12px rgba(0,0,0,0.08)" : "none",
		cursor: isClickable ? "pointer" : "default",
		userSelect: "none" as const,
	};

	return (
		<div
			style={cardStyle}
			role={isClickable ? "button" : undefined}
			tabIndex={isClickable ? 0 : undefined}
			onClick={isClickable ? onClick : undefined}
			onKeyDown={isClickable ? handleKeyDown : undefined}
			onMouseEnter={() => setHovered(true)}
			onMouseLeave={() => setHovered(false)}
		>
			<HeaderRow label={label} icon={icon} infoTooltip={infoTooltip} />
			<span
				style={{
					fontSize: typography.size["2xl"],
					fontWeight: typography.weight.bold,
					color: colors.slate[900],
					lineHeight: 1.2,
				}}
			>
				{value}
			</span>
			{delta !== undefined && (
				<span
					style={{
						fontSize: typography.size.xs,
						color: deltaColor(deltaPositive),
						fontWeight: typography.weight.medium,
					}}
				>
					{delta}
				</span>
			)}
			{sparkline !== undefined && sparkline.length > 0 && (
				<LineChart width={80} height={24} data={sparkline}>
					<Line
						type="monotone"
						dataKey="value"
						stroke={colors.indigo[500]}
						strokeWidth={1.5}
						dot={false}
					/>
				</LineChart>
			)}
		</div>
	);
}
