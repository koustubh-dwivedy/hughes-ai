import { Check } from "lucide-react";
import { useState } from "react";
import { colors, spacing, typography } from "../../theme/tokens";

type StepState = "done" | "current" | "todo";

interface StepperProps {
	stages: readonly string[];
	/** How far the case has progressed (stages before this are done). */
	currentStage: number;
	/** Which stage's detail is being viewed. */
	selected: number;
	onSelect: (index: number) => void;
}

const DOT = 28;

function dotStyle(state: StepState): React.CSSProperties {
	const isDone = state === "done";
	const border = state === "todo" ? colors.slate[300] : colors.slate[800];
	return {
		position: "relative",
		zIndex: 1,
		display: "inline-flex",
		alignItems: "center",
		justifyContent: "center",
		width: DOT,
		height: DOT,
		borderRadius: "9999px",
		backgroundColor: isDone ? colors.slate[800] : colors.white,
		border: `2px solid ${border}`,
		// A soft ring makes the current (progress frontier) dot pop.
		boxShadow:
			state === "current" ? `0 0 0 4px ${colors.slate[200]}` : undefined,
		color: isDone ? colors.white : colors.slate[800],
		fontSize: typography.size.xs,
		fontWeight: typography.weight.semibold,
		flexShrink: 0,
	};
}

function Connector({
	filled,
	half,
}: { filled: boolean; half: "top" | "bottom" }) {
	return (
		<span
			style={{
				position: "absolute",
				left: "50%",
				transform: "translateX(-50%)",
				top: half === "top" ? 0 : "50%",
				height: "50%",
				width: 2,
				backgroundColor: filled ? colors.slate[800] : colors.slate[200],
				zIndex: 0,
			}}
		/>
	);
}

interface StepItemProps {
	stage: string;
	index: number;
	state: StepState;
	selected: boolean;
	first: boolean;
	last: boolean;
	onSelect: (index: number) => void;
	currentStage: number;
}

function rowBackground(selected: boolean, hover: boolean): string {
	if (selected) return colors.slate[100];
	if (hover) return colors.slate[50];
	return "transparent";
}

function rowStyle(
	selected: boolean,
	hover: boolean,
	focus: boolean,
): React.CSSProperties {
	return {
		display: "flex",
		alignItems: "center",
		gap: spacing[3],
		width: "100%",
		textAlign: "left",
		minHeight: 44,
		padding: `${spacing[2]} ${spacing[3]}`,
		background: rowBackground(selected, hover),
		border: "none",
		// Reserve the accent rail so selecting doesn't shift the row.
		borderLeft: `3px solid ${selected ? colors.slate[800] : "transparent"}`,
		borderRadius: `0 ${spacing[2]} ${spacing[2]} 0`,
		cursor: "pointer",
		outline: focus ? `2px solid ${colors.slate[400]}` : "none",
		outlineOffset: -2,
	};
}

function Marker({
	index,
	state,
	first,
	last,
	currentStage,
}: Pick<StepItemProps, "index" | "state" | "first" | "last" | "currentStage">) {
	return (
		<span
			style={{
				position: "relative",
				alignSelf: "stretch",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				width: DOT,
				flexShrink: 0,
			}}
		>
			{!first && <Connector half="top" filled={index <= currentStage} />}
			{!last && <Connector half="bottom" filled={index < currentStage} />}
			<span style={dotStyle(state)} aria-hidden>
				{state === "done" ? <Check size={14} /> : index + 1}
			</span>
		</span>
	);
}

function StepItem({
	stage,
	index,
	state,
	selected,
	first,
	last,
	onSelect,
	currentStage,
}: StepItemProps) {
	const [hover, setHover] = useState(false);
	const [focus, setFocus] = useState(false);
	const emphasize = selected || state === "current";
	return (
		<button
			type="button"
			onClick={() => onSelect(index)}
			onMouseEnter={() => setHover(true)}
			onMouseLeave={() => setHover(false)}
			onFocus={() => setFocus(true)}
			onBlur={() => setFocus(false)}
			aria-current={selected ? "step" : undefined}
			style={rowStyle(selected, hover, focus)}
		>
			<Marker
				index={index}
				state={state}
				first={first}
				last={last}
				currentStage={currentStage}
			/>
			<span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
				<span
					style={{
						fontSize: typography.size.sm,
						fontWeight: emphasize
							? typography.weight.semibold
							: typography.weight.normal,
						color: state === "todo" ? colors.slate[400] : colors.slate[800],
					}}
				>
					{stage}
				</span>
				{state === "current" && (
					<span
						style={{
							fontSize: typography.size.xs,
							color: colors.slate[500],
							letterSpacing: "0.04em",
						}}
					>
						You are here
					</span>
				)}
			</span>
		</button>
	);
}

/** Vertical case-journey rail; clicking a stage shows that stage's panel. */
export default function Stepper({
	stages,
	currentStage,
	selected,
	onSelect,
}: StepperProps) {
	return (
		<nav aria-label="Case journey">
			<div
				style={{
					fontSize: typography.size.xs,
					fontWeight: typography.weight.semibold,
					textTransform: "uppercase",
					letterSpacing: "0.06em",
					color: colors.slate[500],
					padding: `0 ${spacing[3]} ${spacing[2]}`,
				}}
			>
				Case journey
			</div>
			<div style={{ display: "flex", flexDirection: "column" }}>
				{stages.map((stage, i) => (
					<StepItem
						key={stage}
						stage={stage}
						index={i}
						state={
							i < currentStage
								? "done"
								: i === currentStage
									? "current"
									: "todo"
						}
						selected={i === selected}
						first={i === 0}
						last={i === stages.length - 1}
						onSelect={onSelect}
						currentStage={currentStage}
					/>
				))}
			</div>
		</nav>
	);
}
