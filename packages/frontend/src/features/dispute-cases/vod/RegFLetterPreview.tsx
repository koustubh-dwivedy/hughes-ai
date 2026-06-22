import { X } from "lucide-react";
import { colors, spacing } from "../../../theme/tokens";
import ScannedDocument from "../assets/ScannedDocument";
import type { LetterContent } from "../assets/assetContent";
import { formatDate } from "../format";
import type { VodCase } from "../types";

interface Props {
	c: VodCase;
	onClose: () => void;
}

function coverLetter(c: VodCase): LetterContent {
	const v = c.vod;
	const acct = c.subjectAccount.accountNumberMasked;
	return {
		format: "letter",
		kind: "letter",
		title: "Debt verification — cover letter",
		draft: true,
		sender: {
			name: "Cascade Federal Credit Union",
			lines: [
				"Member Resolution Department",
				"1200 Riverside Avenue",
				"Spokane, WA 99201",
			],
		},
		date: formatDate(v.itemizationDate),
		recipient: { name: c.member.name, lines: [c.member.address] },
		re: `Verification of debt — account ${acct}`,
		salutation: `Dear ${c.member.name},`,
		body: [
			"This communication is from a debt collector. This letter provides verification of the debt referenced in your dispute.",
			`The creditor of record is ${v.originalCreditor} and the account number is ${acct}. As of ${v.itemizationDate}, the amount of the debt was $${v.amountAtItemization.toLocaleString()}. Since then: interest $${v.interest.toLocaleString()}, fees $${v.fees.toLocaleString()}, payments −$${v.payments.toLocaleString()}, credits −$${v.credits.toLocaleString()}. The current amount of the debt is $${v.currentAmount.toLocaleString()}.`,
			`You may dispute this debt in writing on or before ${v.disputeWindowEnds}. If you do, collection will pause until we mail you verification.`,
		],
		closing: "Sincerely,",
		signatory: { name: "J. Mercer", title: "Member Resolution Specialist" },
		enclosures: [
			"Signed account agreement",
			"Account statements",
			"Payment history",
		],
	};
}

/**
 * Preview of the auto-assembled debt-verification cover letter, rendered as a
 * clean scanned letter over a blurred backdrop. Mockup only.
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
			<ScannedDocument content={coverLetter(c)} />
		</dialog>
	);
}
