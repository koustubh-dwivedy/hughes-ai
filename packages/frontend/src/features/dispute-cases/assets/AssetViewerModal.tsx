import { X } from "lucide-react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import ScannedDocument from "./ScannedDocument";
import type { AssetContent, TranscriptContent } from "./assetContent";

interface Props {
	content: AssetContent;
	onClose: () => void;
}

function TranscriptCard({ content }: { content: TranscriptContent }) {
	return (
		<div
			style={{
				backgroundColor: colors.white,
				borderRadius: radii.xl,
				width: "min(560px, 92vw)",
				maxHeight: "85vh",
				overflowY: "auto",
				padding: spacing[8],
				boxShadow: "0 20px 60px rgba(15,23,42,0.35)",
			}}
		>
			<p
				style={{
					fontSize: typography.size.xs,
					textTransform: "uppercase",
					letterSpacing: "0.06em",
					color: colors.slate[500],
					margin: 0,
				}}
			>
				{content.header}
			</p>
			<h2
				style={{
					fontSize: typography.size.lg,
					fontWeight: typography.weight.semibold,
					color: colors.slate[900],
					margin: `${spacing[2]} 0 ${spacing[4]}`,
				}}
			>
				{content.title}
			</h2>
			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}
			>
				{content.lines.map((l, i) => (
					<div
						key={`${i}-${l.speaker}`}
						style={{ fontSize: typography.size.sm }}
					>
						<span
							style={{
								fontWeight: typography.weight.semibold,
								color: colors.slate[700],
							}}
						>
							{l.speaker}:
						</span>{" "}
						<span style={{ color: colors.slate[800] }}>{l.text}</span>
					</div>
				))}
			</div>
		</div>
	);
}

/**
 * Opens a mocked file asset over a blurred backdrop. Letters/forms render as a
 * clean scanned printed page; call recordings render as a transcript. Demo only.
 */
export default function AssetViewerModal({ content, onClose }: Props) {
	return (
		<dialog
			open
			aria-label={`${content.title} preview`}
			onKeyDown={(e) => {
				if (e.key === "Escape") onClose();
			}}
			style={{
				position: "fixed",
				inset: 0,
				zIndex: 500,
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				border: "none",
				background: "rgba(15,23,42,0.5)",
				backdropFilter: "blur(4px)",
				WebkitBackdropFilter: "blur(4px)",
				width: "100%",
				height: "100%",
				maxWidth: "none",
				maxHeight: "none",
			}}
		>
			<button
				type="button"
				aria-label="Close"
				onClick={onClose}
				style={{
					position: "fixed",
					top: spacing[4],
					right: spacing[4],
					display: "inline-flex",
					alignItems: "center",
					justifyContent: "center",
					width: 36,
					height: 36,
					borderRadius: "9999px",
					border: "none",
					backgroundColor: colors.white,
					color: colors.slate[700],
					cursor: "pointer",
					boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
				}}
			>
				<X size={18} />
			</button>
			{content.format === "transcript" ? (
				<TranscriptCard content={content} />
			) : (
				<ScannedDocument content={content} />
			)}
		</dialog>
	);
}
