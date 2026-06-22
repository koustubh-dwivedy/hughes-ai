import { X } from "lucide-react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { VodCase } from "../types";

interface Props {
	c: VodCase;
	onClose: () => void;
}

const lineStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[800],
	margin: `${spacing[1]} 0`,
};

/**
 * A read-only preview of the auto-assembled Reg F validation letter. Mockup
 * only — renders the source-tagged fields as a formatted notice.
 */
export default function RegFLetterPreview({ c, onClose }: Props) {
	const v = c.vod;
	return (
		<dialog
			open
			aria-label="Validation letter preview"
			style={{
				position: "fixed",
				inset: 0,
				zIndex: 400,
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				border: "none",
				background: "rgba(15,23,42,0.5)",
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
					padding: spacing[8],
					width: "min(560px, 92vw)",
					maxHeight: "85vh",
					overflowY: "auto",
					position: "relative",
				}}
			>
				<button
					type="button"
					aria-label="Close"
					onClick={onClose}
					style={{
						position: "absolute",
						top: spacing[4],
						right: spacing[4],
						background: "none",
						border: "none",
						cursor: "pointer",
						color: colors.slate[500],
					}}
				>
					<X size={18} />
				</button>
				<p
					style={{
						fontSize: typography.size.xs,
						textTransform: "uppercase",
						letterSpacing: "0.06em",
						color: colors.slate[500],
						margin: 0,
					}}
				>
					Debt verification — cover letter (DRAFT)
				</p>
				<h2
					style={{
						fontSize: typography.size.lg,
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
						margin: `${spacing[2]} 0 ${spacing[4]}`,
					}}
				>
					This is a communication from a debt collector.
				</h2>
				<p style={lineStyle}>
					To: {c.member.name}, {c.member.address}
				</p>
				<p style={lineStyle}>Creditor: {v.originalCreditor}</p>
				<p style={lineStyle}>
					Account number: {c.subjectAccount.accountNumberMasked}
				</p>
				<hr
					style={{
						border: 0,
						borderTop: `1px solid ${colors.slate[200]}`,
						margin: `${spacing[4]} 0`,
					}}
				/>
				<p style={lineStyle}>
					As of {v.itemizationDate}, the amount of the debt was $
					{v.amountAtItemization.toLocaleString()}.
				</p>
				<p style={lineStyle}>
					Between then and today: interest ${v.interest.toLocaleString()}, fees
					${v.fees.toLocaleString()}, payments −${v.payments.toLocaleString()},
					credits −${v.credits.toLocaleString()}.
				</p>
				<p style={{ ...lineStyle, fontWeight: typography.weight.semibold }}>
					Current amount of the debt: ${v.currentAmount.toLocaleString()}.
				</p>
				<hr
					style={{
						border: 0,
						borderTop: `1px solid ${colors.slate[200]}`,
						margin: `${spacing[4]} 0`,
					}}
				/>
				<p style={lineStyle}>
					You may dispute this debt in writing on or before{" "}
					{v.disputeWindowEnds}. If you do, collection will pause until we mail
					you verification.
				</p>
			</div>
		</dialog>
	);
}
