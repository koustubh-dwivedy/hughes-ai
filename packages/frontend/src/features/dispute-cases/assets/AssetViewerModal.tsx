import { X } from "lucide-react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { AssetContent } from "./assetContent";

interface Props {
	content: AssetContent;
	onClose: () => void;
}

function Transcript({
	lines,
}: { lines: NonNullable<AssetContent["transcript"]> }) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}>
			{lines.map((l, i) => (
				<div key={`${i}-${l.speaker}`} style={{ fontSize: typography.size.sm }}>
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
	);
}

/**
 * Opens a mocked file asset in a centered "document" frame over a blurred,
 * dimmed backdrop. Demo only — content is illustrative.
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
				background: "rgba(15,23,42,0.45)",
				backdropFilter: "blur(4px)",
				WebkitBackdropFilter: "blur(4px)",
				width: "100%",
				height: "100%",
				maxWidth: "none",
				maxHeight: "none",
			}}
		>
			<div
				style={{
					backgroundColor: colors.white,
					borderRadius: radii.xl,
					width: "min(620px, 92vw)",
					maxHeight: "86vh",
					overflowY: "auto",
					position: "relative",
					boxShadow: "0 20px 60px rgba(15,23,42,0.35)",
				}}
			>
				<div
					style={{
						display: "flex",
						alignItems: "center",
						justifyContent: "space-between",
						padding: `${spacing[3]} ${spacing[5]}`,
						borderBottom: `1px solid ${colors.slate[200]}`,
						backgroundColor: colors.slate[50],
						borderTopLeftRadius: radii.xl,
						borderTopRightRadius: radii.xl,
					}}
				>
					<span
						style={{
							fontSize: typography.size.xs,
							textTransform: "uppercase",
							letterSpacing: "0.06em",
							color: colors.slate[500],
						}}
					>
						{content.letterhead}
					</span>
					<button
						type="button"
						aria-label="Close"
						onClick={onClose}
						style={{
							background: "none",
							border: "none",
							cursor: "pointer",
							color: colors.slate[500],
						}}
					>
						<X size={18} />
					</button>
				</div>
				<div
					style={{
						padding: spacing[8],
						display: "flex",
						flexDirection: "column",
						gap: spacing[4],
					}}
				>
					<h2
						style={{
							margin: 0,
							fontSize: typography.size.lg,
							fontWeight: typography.weight.semibold,
							color: colors.slate[900],
						}}
					>
						{content.title}
					</h2>
					<div
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
							gap: spacing[3],
						}}
					>
						{content.meta.map((m) => (
							<div key={m.label}>
								<div
									style={{
										fontSize: typography.size.xs,
										color: colors.slate[500],
									}}
								>
									{m.label}
								</div>
								<div
									style={{
										fontSize: typography.size.sm,
										color: colors.slate[900],
									}}
								>
									{m.value}
								</div>
							</div>
						))}
					</div>
					{content.transcript ? (
						<Transcript lines={content.transcript} />
					) : (
						content.paragraphs.map((p, i) => (
							<p
								key={`${i}-${p.slice(0, 12)}`}
								style={{
									margin: 0,
									fontSize: typography.size.sm,
									lineHeight: 1.6,
									color: colors.slate[700],
								}}
							>
								{p}
							</p>
						))
					)}
					<p
						style={{
							margin: 0,
							marginTop: spacing[2],
							fontSize: typography.size.xs,
							color: colors.slate[400],
						}}
					>
						Illustrative mock document — not a real file.
					</p>
				</div>
			</div>
		</dialog>
	);
}
