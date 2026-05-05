/**
 * Clarification control (HUG-179).
 *
 * When the agent's terminal tool was `clarify` (not `final_answer`),
 * the latest persisted tool message contains `{ question, options[] }`
 * in its content blob. Render the question + each option as a button;
 * a click submits the chosen option as the next user message.
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { ThreadMessageWire } from "../api";

interface ClarifyPayload {
	question?: string;
	options?: string[];
}

interface Props {
	message: ThreadMessageWire | null;
	onSubmit: (option: string) => void;
}

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
	padding: spacing[3],
	background: colors.slate[50],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.lg,
	margin: spacing[3],
};

const questionStyle: React.CSSProperties = {
	fontSize: typography.size.base,
	color: colors.slate[800],
	fontWeight: typography.weight.medium,
};

const optionGroupStyle: React.CSSProperties = {
	display: "flex",
	flexWrap: "wrap",
	gap: spacing[2],
};

const buttonStyle: React.CSSProperties = {
	background: colors.white,
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.md,
	padding: `${spacing[2]} ${spacing[3]}`,
	fontSize: typography.size.sm,
	color: colors.slate[700],
	cursor: "pointer",
	fontFamily: typography.fontFamily,
};

function isClarifyToolMessage(msg: ThreadMessageWire): boolean {
	if (msg.role !== "tool") return false;
	const results = msg.tool_results;
	if (!results || results.length === 0) return false;
	const first = results[0] as { name?: string };
	return first.name === "clarify";
}

function parseClarify(msg: ThreadMessageWire): ClarifyPayload {
	if (!msg.content) return {};
	try {
		return JSON.parse(msg.content) as ClarifyPayload;
	} catch {
		return {};
	}
}

export default function ClarificationControl({ message, onSubmit }: Props) {
	if (!message || !isClarifyToolMessage(message)) return null;
	const payload = parseClarify(message);
	const question = payload.question ?? "Could you clarify?";
	const options = payload.options ?? [];
	if (options.length === 0) return null;
	return (
		<section
			aria-label="Agent clarification"
			role="group"
			style={wrapperStyle}
		>
			<div style={questionStyle}>{question}</div>
			<div style={optionGroupStyle}>
				{options.map((opt) => (
					<button
						key={opt}
						type="button"
						style={buttonStyle}
						onClick={() => onSubmit(opt)}
					>
						{opt}
					</button>
				))}
			</div>
		</section>
	);
}
