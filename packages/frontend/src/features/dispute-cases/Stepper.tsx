import { Check } from "lucide-react";
import { colors, spacing, typography } from "../../theme/tokens";

type StepState = "done" | "active" | "todo";

interface StepperProps {
	stages: readonly string[];
	/** How far the case has progressed (stages before this are done). */
	currentStage: number;
	/** Which stage's detail is being viewed. */
	selected: number;
	onSelect: (index: number) => void;
}

function dotStyle(state: StepState): React.CSSProperties {
	const border = state === "todo" ? colors.slate[300] : colors.slate[800];
	return {
		display: "inline-flex",
		alignItems: "center",
		justifyContent: "center",
		width: 28,
		height: 28,
		borderRadius: "9999px",
		backgroundColor: state === "done" ? colors.slate[800] : colors.white,
		border: `2px solid ${border}`,
		color: state === "done" ? colors.white : colors.slate[800],
		fontSize: typography.size.xs,
		fontWeight: typography.weight.semibold,
		flexShrink: 0,
	};
}

interface StepItemProps {
	stage: string;
	index: number;
	state: StepState;
	selected: boolean;
	last: boolean;
	onSelect: (index: number) => void;
}

function StepItem({
	stage,
	index,
	state,
	selected,
	last,
	onSelect,
}: StepItemProps) {
	return (
		<div style={{ display: "flex", alignItems: "center", gap: spacing[1] }}>
			<button
				type="button"
				onClick={() => onSelect(index)}
				aria-current={selected ? "step" : undefined}
				style={{
					display: "flex",
					alignItems: "center",
					gap: spacing[2],
					background: selected ? colors.slate[100] : "transparent",
					border: "none",
					borderRadius: 9999,
					padding: `${spacing[1]} ${spacing[2]}`,
					cursor: "pointer",
				}}
			>
				<span style={dotStyle(state)}>
					{state === "done" ? <Check size={14} /> : index + 1}
				</span>
				<span
					style={{
						fontSize: typography.size.sm,
						fontWeight: selected
							? typography.weight.semibold
							: typography.weight.normal,
						color: state === "todo" ? colors.slate[400] : colors.slate[800],
						whiteSpace: "nowrap",
					}}
				>
					{stage}
				</span>
			</button>
			{!last && (
				<span
					style={{
						width: spacing[5],
						height: 2,
						backgroundColor:
							state === "done" ? colors.slate[800] : colors.slate[200],
					}}
				/>
			)}
		</div>
	);
}

/** Horizontal lifecycle stepper; clicking a stage shows that stage's panel. */
export default function Stepper({
	stages,
	currentStage,
	selected,
	onSelect,
}: StepperProps) {
	return (
		<div
			style={{
				display: "flex",
				alignItems: "center",
				gap: spacing[1],
				overflowX: "auto",
				padding: `${spacing[2]} 0`,
			}}
		>
			{stages.map((stage, i) => (
				<StepItem
					key={stage}
					stage={stage}
					index={i}
					state={
						i < currentStage ? "done" : i === currentStage ? "active" : "todo"
					}
					selected={i === selected}
					last={i === stages.length - 1}
					onSelect={onSelect}
				/>
			))}
		</div>
	);
}
