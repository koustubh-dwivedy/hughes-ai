import { X } from "lucide-react";
import { colors, spacing } from "../../../theme/tokens";
import ScannedDocument, { type ScannedDoc } from "../assets/ScannedDocument";
import type { VodCase } from "../types";

interface Props {
	c: VodCase;
	onClose: () => void;
}

function coverLetter(c: VodCase): ScannedDoc {
	const v = c.vod;
	return {
		letterhead: "Cascade Federal Credit Union",
		subhead: "Debt verification — cover letter (DRAFT)",
		meta: [
			{ label: "To", value: `${c.member.name}, ${c.member.address}` },
			{ label: "Creditor", value: v.originalCreditor },
			{ label: "Account", value: c.subjectAccount.accountNumberMasked },
		],
		paragraphs: [
			"This is a communication from a debt collector. This letter provides verification of the debt referenced in your dispute.",
			`As of ${v.itemizationDate}, the amount of the debt was $${v.amountAtItemization.toLocaleString()}. Between then and today: interest $${v.interest.toLocaleString()}, fees $${v.fees.toLocaleString()}, payments −$${v.payments.toLocaleString()}, credits −$${v.credits.toLocaleString()}. The current amount of the debt is $${v.currentAmount.toLocaleString()}.`,
			`You may dispute this debt in writing on or before ${v.disputeWindowEnds}. If you do, collection will pause until we mail you verification.`,
		],
		signature: { name: "J. Mercer", title: "Member Resolution Specialist" },
		stamps: [{ text: "DRAFT", tone: "red" }],
	};
}

/**
 * Preview of the auto-assembled debt-verification cover letter, rendered as a
 * heavy/aged scanned page over a blurred backdrop. Mockup only.
 */
export default function RegFLetterPreview({ c, onClose }: Props) {
	return (
		<dialog
			open
			aria-label="Validation letter preview"
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
			<ScannedDocument doc={coverLetter(c)} />
		</dialog>
	);
}
