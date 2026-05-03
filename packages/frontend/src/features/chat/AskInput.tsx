import { Clock } from "lucide-react";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../theme/tokens";

interface Props {
	onSubmit: (question: string) => void;
	loading: boolean;
	onOpenHistory?: () => void;
}

export default function AskInput({ onSubmit, loading, onOpenHistory }: Props) {
	const [value, setValue] = useState("");

	function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		const q = value.trim();
		if (q) onSubmit(q);
	}

	return (
		<form
			onSubmit={handleSubmit}
			style={{
				display: "flex",
				gap: spacing[2],
				alignItems: "center",
				padding: spacing[3],
				background: colors.white,
				border: `1px solid ${colors.slate[200]}`,
				borderRadius: radii.lg,
			}}
		>
			{onOpenHistory && (
				<button
					type="button"
					aria-label="Open conversation history"
					onClick={onOpenHistory}
					style={{
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						width: 32,
						height: 32,
						border: `1px solid ${colors.slate[200]}`,
						borderRadius: radii.md,
						background: colors.slate[50],
						color: colors.slate[600],
						cursor: "pointer",
						flexShrink: 0,
					}}
				>
					<Clock size={16} />
				</button>
			)}
			<input
				value={value}
				onChange={(e) => setValue(e.target.value)}
				placeholder="Ask a question about lending…"
				disabled={loading}
				style={{
					flex: 1,
					padding: `${spacing[2]} ${spacing[3]}`,
					border: "none",
					outline: "none",
					fontSize: typography.size.sm,
					fontFamily: typography.fontFamily,
					color: colors.slate[800],
					background: "transparent",
				}}
			/>
			<button
				type="submit"
				disabled={loading || value.trim() === ""}
				style={{
					padding: `${spacing[2]} ${spacing[4]}`,
					backgroundColor:
						loading || value.trim() === ""
							? colors.slate[200]
							: colors.indigo[600],
					color:
						loading || value.trim() === "" ? colors.slate[400] : colors.white,
					border: "none",
					borderRadius: radii.md,
					fontSize: typography.size.sm,
					fontWeight: typography.weight.medium,
					cursor: loading || value.trim() === "" ? "not-allowed" : "pointer",
					fontFamily: typography.fontFamily,
				}}
			>
				{loading ? "Loading…" : "Ask"}
			</button>
		</form>
	);
}
