import type React from "react";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tooltip from "../Tooltip";
import { CountUp, motionDurations, usePrefersReducedMotion } from "../motion";
import type { KpiTileProps } from "./types";

const POSITIVE_COLOR = "#16a34a";
const NEGATIVE_COLOR = "#dc2626";
const NEUTRAL_COLOR = colors.slate[400];

function deltaColor(deltaPositive: boolean | undefined): string {
	if (deltaPositive === true) return POSITIVE_COLOR;
	if (deltaPositive === false) return NEGATIVE_COLOR;
	return NEUTRAL_COLOR;
}

interface HoverVisuals {
	boxShadow: string;
	transform: string;
	transition: string;
}

function hoverVisuals(hovered: boolean, reduced: boolean): HoverVisuals {
	if (reduced) {
		return { boxShadow: "none", transform: "none", transition: "none" };
	}
	return {
		boxShadow: hovered ? "0 4px 12px rgba(0,0,0,0.08)" : "none",
		transform: hovered ? "translateY(-2px)" : "none",
		transition: `box-shadow ${motionDurations.hoverLift}ms ease, transform ${motionDurations.hoverLift}ms ease`,
	};
}

interface HeaderRowProps {
	label: string;
	icon?: React.ReactNode;
	infoTooltip?: string;
}

function HeaderRow({ label, icon, infoTooltip }: HeaderRowProps) {
	const labelEl = (
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
	);
	return (
		<div style={{ display: "flex", alignItems: "center", gap: spacing[1] }}>
			{icon !== undefined && (
				<span
					style={{ fontSize: 16, color: colors.indigo[500], lineHeight: 1 }}
				>
					{icon}
				</span>
			)}
			{labelEl}
			{infoTooltip !== undefined && (
				<Tooltip
					label={infoTooltip}
					multiline
					w={300}
					withArrow
					position="top"
				>
					<span
						aria-label={infoTooltip}
						role="img"
						style={{
							display: "inline-flex",
							alignItems: "center",
							justifyContent: "center",
							width: 14,
							height: 14,
							borderRadius: "50%",
							border: `1px solid ${colors.slate[300]}`,
							color: colors.slate[400],
							fontSize: 10,
							fontWeight: typography.weight.semibold,
							marginLeft: spacing[1],
							cursor: "help",
							lineHeight: 1,
						}}
					>
						i
					</span>
				</Tooltip>
			)}
		</div>
	);
}

export default function KpiTile({
	label,
	value,
	delta,
	deltaLabel,
	deltaPositive,
	context,
	icon,
	infoTooltip,
	onClick,
	loading = false,
}: KpiTileProps) {
	const [hovered, setHovered] = useState(false);
	const reducedMotion = usePrefersReducedMotion();

	if (loading) {
		return (
			<output
				aria-label="loading"
				style={{
					display: "block",
					width: 180,
					height: 110,
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

	const visuals = hoverVisuals(hovered, reducedMotion);
	const cardStyle: React.CSSProperties = {
		display: "inline-flex",
		flexDirection: "column",
		gap: spacing[1],
		padding: spacing[4],
		border: `1px solid ${colors.slate[200]}`,
		borderRadius: radii.lg,
		backgroundColor: colors.white,
		minWidth: 180,
		...visuals,
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
				<CountUp value={value} />
			</span>
			{delta !== undefined && (
				<span
					style={{
						fontSize: typography.size.xs,
						color: deltaColor(deltaPositive),
						fontWeight: typography.weight.medium,
						display: "inline-flex",
						alignItems: "center",
						gap: spacing[1],
					}}
				>
					<span>{delta}</span>
					{deltaLabel !== undefined && (
						<span
							style={{
								color: colors.slate[400],
								fontWeight: typography.weight.normal,
							}}
						>
							{deltaLabel}
						</span>
					)}
				</span>
			)}
			{context !== undefined && (
				<span
					style={{
						fontSize: typography.size.xs,
						color: colors.slate[500],
						lineHeight: 1.4,
						marginTop: spacing[1],
					}}
				>
					{context}
				</span>
			)}
		</div>
	);
}
