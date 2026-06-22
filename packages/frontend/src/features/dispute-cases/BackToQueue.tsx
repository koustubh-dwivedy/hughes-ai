import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";

/** Left-aligned breadcrumb back link, rendered above a Dispute Center page header. */
export default function BackToQueue() {
	return (
		<Link
			to="/disputes"
			style={{
				alignSelf: "flex-start",
				display: "inline-flex",
				alignItems: "center",
				gap: spacing[1],
				padding: `${spacing[1]} ${spacing[2]}`,
				marginBottom: spacing[3],
				borderRadius: radii.md,
				border: `1px solid ${colors.slate[200]}`,
				backgroundColor: colors.white,
				fontSize: typography.size.sm,
				fontWeight: typography.weight.medium,
				color: colors.slate[700],
				textDecoration: "none",
			}}
		>
			<ArrowLeft size={16} /> Back to Case Queue
		</Link>
	);
}
