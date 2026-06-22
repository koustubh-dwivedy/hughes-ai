import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Banner from "../../../ui/primitives/Banner";
import type { Signoff } from "../data/caseProgressStore";

export interface ApprovalOption {
	value: string;
	label: string;
}

interface Props {
	title: string;
	/** The AI's recommendation, shown as read-only context. */
	recommendationLabel?: string;
	options: ApprovalOption[];
	value: Signoff;
	onChange: (next: Signoff) => void;
}

const textareaStyle: React.CSSProperties = {
	width: "100%",
	minHeight: 64,
	resize: "vertical",
	padding: spacing[2],
	borderRadius: radii.md,
	border: `1px solid ${colors.slate[300]}`,
	fontFamily: typography.fontFamily,
	fontSize: typography.size.sm,
	color: colors.slate[900],
	boxSizing: "border-box",
};

function optionStyle(active: boolean): React.CSSProperties {
	return {
		padding: `${spacing[1]} ${spacing[3]}`,
		borderRadius: radii.md,
		border: `1px solid ${active ? colors.slate[800] : colors.slate[300]}`,
		backgroundColor: active ? colors.slate[800] : colors.white,
		color: active ? colors.white : colors.slate[700],
		fontSize: typography.size.sm,
		fontWeight: typography.weight.medium,
		cursor: "pointer",
	};
}

/**
 * Mandatory human sign-off on an AI step: the reviewer must select an option
 * AND write notes. The stage's Continue/Resolve stays disabled until both are
 * present (enforced by the stepper via `signoffComplete`). Edits the session
 * store live; revisiting a stage shows the recorded sign-off.
 */
export default function ApprovalGate({
	title,
	recommendationLabel,
	options,
	value,
	onChange,
}: Props) {
	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: spacing[3],
				padding: spacing[4],
				borderRadius: radii.lg,
				border: `1px solid ${colors.slate[200]}`,
				backgroundColor: colors.white,
			}}
		>
			<Banner
				variant="warning"
				message="Human sign-off required — select an option and add notes to proceed."
			/>
			<span
				style={{
					fontSize: typography.size.sm,
					fontWeight: typography.weight.semibold,
					color: colors.slate[900],
				}}
			>
				{title}
			</span>
			{recommendationLabel && (
				<span
					style={{ fontSize: typography.size.sm, color: colors.slate[600] }}
				>
					AI recommends: <strong>{recommendationLabel}</strong>
				</span>
			)}
			<div style={{ display: "flex", gap: spacing[2], flexWrap: "wrap" }}>
				{options.map((o) => (
					<button
						key={o.value}
						type="button"
						aria-pressed={value.option === o.value}
						onClick={() => onChange({ ...value, option: o.value })}
						style={optionStyle(value.option === o.value)}
					>
						{o.label}
					</button>
				))}
			</div>
			<label
				style={{
					display: "flex",
					flexDirection: "column",
					gap: spacing[1],
					fontSize: typography.size.xs,
					color: colors.slate[500],
				}}
			>
				Notes (required)
				<textarea
					aria-label="Sign-off notes"
					value={value.comments}
					onChange={(e) => onChange({ ...value, comments: e.target.value })}
					placeholder="Record your rationale / what you reviewed…"
					style={textareaStyle}
				/>
			</label>
		</div>
	);
}
