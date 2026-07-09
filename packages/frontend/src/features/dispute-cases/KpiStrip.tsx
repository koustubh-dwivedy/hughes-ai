import { KpiGrid, default as KpiTile } from "../../ui/primitives/KpiTile";
import { getOverride, useCaseProgressVersion } from "./data/caseProgressStore";
import { daysUntil } from "./format";
import type { DisputeCase } from "./types";

function isOpen(c: DisputeCase): boolean {
	const status = getOverride(c.id)?.status ?? c.status;
	return status !== "Resolved";
}

/**
 * The Dispute Center compliance strip: open volume by type, SLA risk (30-day
 * FCRA/FDCPA + 4-business-day §605B clocks), aging, and outstanding bureau
 * actions (uncleared XB flags + pending blocks).
 */
export default function KpiStrip({ cases }: { cases: DisputeCase[] }) {
	// Subscribe so resolving a case this session updates the open counts.
	useCaseProgressVersion();
	const open = cases.filter(isOpen);
	const openDa = open.filter((c) => c.type === "DATA_ACCURACY").length;
	const openFraud = open.filter((c) => c.type === "FRAUD").length;

	const approaching = open.filter((c) => daysUntil(c.slaDueDate) <= 2).length;

	const unclearedXb = cases.filter((c) => isOpen(c) && c.ccc === "XB").length;
	const pendingBlocks = cases.filter(
		(c) => c.type === "FRAUD" && isOpen(c) && !c.fraud.blockApplied,
	).length;

	return (
		<KpiGrid>
			<KpiTile
				label="Open cases"
				value={String(open.length)}
				context={`${openDa} data-accuracy · ${openFraud} fraud`}
			/>
			<KpiTile
				label="SLA risk"
				value={String(approaching)}
				context="≤ 2 days to deadline"
				deltaPositive={approaching === 0}
			/>
			<KpiTile
				label="Avg cycle time"
				value="11 days"
				context="oldest open: 21 days"
			/>
			<KpiTile
				label="Outstanding bureau actions"
				value={String(unclearedXb + pendingBlocks)}
				context={`${unclearedXb} uncleared XB · ${pendingBlocks} pending blocks`}
			/>
		</KpiGrid>
	);
}
