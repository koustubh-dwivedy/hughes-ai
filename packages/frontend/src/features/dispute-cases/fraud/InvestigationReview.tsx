import { spacing } from "../../../theme/tokens";
import Banner from "../../../ui/primitives/Banner";
import type { AiInvestigation, HumanAction } from "../ai/aiTypes";
import type { TriangulationRow } from "../types";
import EvidencePanel from "./EvidencePanel";
import VerdictPanel from "./VerdictPanel";

interface Props {
	investigation: AiInvestigation;
	rows: TriangulationRow[];
	memberName?: string;
	decision: HumanAction | null;
	onDecision: (action: HumanAction | null) => void;
}

/**
 * Decision-first two-column review of the agentic investigation. Left: the
 * agent's synthesis verdict + gates + inline decision + reasoning trace.
 * Right: the evidence, framed by stance, each signal drillable to the agent's
 * resolution, raw datapoints, and source document. Stacks on narrow screens.
 */
export default function InvestigationReview({
	investigation,
	rows,
	memberName,
	decision,
	onDecision,
}: Props) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<Banner
				variant="warning"
				message="AI-assisted investigation — validate the evidence before acting."
			/>
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
					gap: spacing[5],
					alignItems: "start",
				}}
			>
				<VerdictPanel
					investigation={investigation}
					decision={decision}
					onDecision={onDecision}
				/>
				<EvidencePanel rows={rows} memberName={memberName} />
			</div>
		</div>
	);
}
