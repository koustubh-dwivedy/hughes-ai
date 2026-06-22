import { spacing } from "../../../theme/tokens";
import Banner from "../../../ui/primitives/Banner";
import type { AiInvestigation } from "../ai/aiTypes";
import type { TriangulationRow } from "../types";
import EvidencePanel from "./EvidencePanel";
import VerdictPanel from "./VerdictPanel";

interface Props {
	investigation: AiInvestigation;
	rows: TriangulationRow[];
	memberName?: string;
}

/**
 * Two-column review of the agentic investigation. Left: AI's synthesis verdict
 * + gates + reasoning trace. Right: the evidence, framed by stance, each signal
 * drillable to its resolution, raw datapoints, and source document. The human
 * signs off at the Decide step. Stacks on narrow screens.
 */
export default function InvestigationReview({
	investigation,
	rows,
	memberName,
}: Props) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<Banner
				variant="warning"
				message="AI-assisted investigation — validate the evidence before signing off."
			/>
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
					gap: spacing[5],
					alignItems: "start",
				}}
			>
				<VerdictPanel investigation={investigation} />
				<EvidencePanel rows={rows} memberName={memberName} />
			</div>
		</div>
	);
}
