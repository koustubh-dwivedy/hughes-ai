/**
 * Composer for the conversational surface (HUG-179).
 *
 * Multi-line textarea wired to the threadSlice's `draftInput`. Submits
 * on Cmd+Enter (Mac) / Ctrl+Enter, or via the explicit Send button. The
 * parent decides what to do with the submitted text — typically: append
 * a user message, fire the postMessage SSE mutation, clear the draft.
 */

import { useCallback } from "react";
import { useAppDispatch, useAppSelector } from "../../../shared/api/hooks";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { setDraft } from "../threadSlice";

interface Props {
	onSubmit: (content: string) => void;
	disabled?: boolean;
}

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	gap: spacing[2],
	padding: spacing[3],
	background: colors.white,
	borderTop: `1px solid ${colors.slate[200]}`,
};

const textareaStyle: React.CSSProperties = {
	flex: 1,
	minHeight: 60,
	maxHeight: 200,
	resize: "vertical",
	padding: spacing[2],
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.md,
	fontSize: typography.size.sm,
	fontFamily: typography.fontFamily,
	color: colors.slate[800],
};

const buttonStyle: React.CSSProperties = {
	background: colors.indigo[700],
	color: colors.white,
	border: "none",
	borderRadius: radii.md,
	padding: `0 ${spacing[4]}`,
	cursor: "pointer",
	fontSize: typography.size.sm,
	fontFamily: typography.fontFamily,
	fontWeight: typography.weight.medium,
	alignSelf: "flex-end",
};

const buttonDisabledStyle: React.CSSProperties = {
	...buttonStyle,
	background: colors.slate[300],
	color: colors.slate[600],
	cursor: "not-allowed",
};

export default function ComposerInput({ onSubmit, disabled = false }: Props) {
	const dispatch = useAppDispatch();
	const draft = useAppSelector((s) => s.thread.draftInput);

	const handleSubmit = useCallback(() => {
		const trimmed = draft.trim();
		if (trimmed.length === 0 || disabled) return;
		onSubmit(trimmed);
		dispatch(setDraft(""));
	}, [draft, disabled, onSubmit, dispatch]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
			if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
				e.preventDefault();
				handleSubmit();
			}
		},
		[handleSubmit],
	);

	const isDisabled = disabled || draft.trim().length === 0;

	return (
		<div style={wrapperStyle}>
			<textarea
				aria-label="Ask Hughes"
				placeholder="Ask anything about the portfolio…"
				value={draft}
				onChange={(e) => dispatch(setDraft(e.target.value))}
				onKeyDown={handleKeyDown}
				style={textareaStyle}
				disabled={disabled}
			/>
			<button
				type="button"
				onClick={handleSubmit}
				disabled={isDisabled}
				style={isDisabled ? buttonDisabledStyle : buttonStyle}
			>
				Send
			</button>
		</div>
	);
}
