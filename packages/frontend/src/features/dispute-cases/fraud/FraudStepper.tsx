import { useState } from "react";
import { colors, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import StageFooter from "../StageFooter";
import Stepper from "../Stepper";
import IntakeExtractionPanel from "../ai/IntakeExtractionPanel";
import ProvenanceBadge from "../ai/ProvenanceBadge";
import { FRAUD_PROVENANCE, type HumanAction } from "../ai/aiTypes";
import { Field, FieldGrid, Flag, SectionCard } from "../caseUi";
import { getCaseAi } from "../data/aiInvestigations";
import {
	resolveCase,
	setDecision as setDecisionStore,
	setStage,
	useCaseProgress,
} from "../data/caseProgressStore";
import { formatDate } from "../format";
import { FRAUD_STAGES, type FraudCase } from "../types";
import InvestigationReview from "./InvestigationReview";

const DECIDE_INDEX = 2; // gating point: a disposition is required to continue

function fraudOutcome(decision: HumanAction | null): string {
	return decision === "overridden"
		? "Denied — first-party (kept furnishing)"
		: "Blocked & suppressed (§605B)";
}

interface StageProps {
	c: FraudCase;
	decision: HumanAction | null;
	onDecision: (action: HumanAction | null) => void;
}

const DECISION_SUMMARY: Record<HumanAction, string> = {
	approved: "Approved AI recommendation",
	overridden: "Overrode AI recommendation",
	more_info: "Requested more information",
};

function IntakeStage({ c }: StageProps) {
	const f = c.fraud;
	const ai = getCaseAi(c.id);
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			{ai?.intake && <IntakeExtractionPanel extraction={ai.intake} />}
			<FieldGrid>
				<Field label="Channel" value={c.channel} />
				<Field label="Received" value={formatDate(c.receivedDate)} />
				<Field label="Fraud sub-type" value={f.subType} />
				<Field
					label="Identity Theft Report"
					value={
						f.identityTheftReport.onFile
							? (f.identityTheftReport.type ?? "On file")
							: "Not on file"
					}
				/>
				<Field
					label="Report reference"
					value={f.identityTheftReport.referenceNumber ?? "—"}
				/>
				<Field
					label="Jurisdiction"
					value={f.identityTheftReport.jurisdiction ?? "—"}
				/>
			</FieldGrid>
		</div>
	);
}

function TriangulateStage({ c, decision, onDecision }: StageProps) {
	const ai = getCaseAi(c.id);
	if (!ai?.investigation) return null;
	return (
		<InvestigationReview
			investigation={ai.investigation}
			rows={c.fraud.triangulation}
			memberName={c.member.name}
			decision={decision}
			onDecision={onDecision}
		/>
	);
}

function DecideStage({ decision }: StageProps) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<Field
				label="Recorded decision"
				value={
					decision
						? DECISION_SUMMARY[decision]
						: "Pending — decide on the Triangulate ID step"
				}
			/>
			<p
				style={{
					fontSize: typography.size.sm,
					color: colors.slate[600],
					margin: 0,
				}}
			>
				Third-party → block under §605B. First-party → deny and keep furnishing.
			</p>
		</div>
	);
}

function SuppressBlockStage({ c }: StageProps) {
	const f = c.fraud;
	const blockLabel = f.blockApplied
		? "Block applied"
		: `${f.blockBusinessDaysRemaining} business day${f.blockBusinessDaysRemaining === 1 ? "" : "s"} left`;
	const blockVariant = f.blockApplied
		? "success"
		: f.blockBusinessDaysRemaining <= 1
			? "danger"
			: "warning";
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<p
				style={{
					fontSize: typography.size.sm,
					color: colors.slate[600],
					margin: 0,
				}}
			>
				Suppress our furnishing of the tradeline; the §605B block on the
				consumer's report is the bureau's action. The block clock runs in
				parallel with the investigation — suppress first, finalize disposition
				after.
			</p>
			<Tag label={`§605B clock: ${blockLabel}`} variant={blockVariant} />
			<div style={{ display: "flex", gap: spacing[6], flexWrap: "wrap" }}>
				<Flag label="Furnishing suppressed" on={f.blockApplied} />
				<Flag label="Prevent re-furnishing" on={f.preventRefurnish} />
				<Flag label="Collection prohibited" on={f.collectionProhibition} />
			</div>
			<div
				style={{
					display: "flex",
					gap: spacing[3],
					alignItems: "center",
					flexWrap: "wrap",
				}}
			>
				<span>Metro 2 / e-OSCAR:</span>
				<Tag label="Tradeline suppressed" variant="info" />
				<Tag label="AUD submitted" variant="info" />
				{c.ccc && <Tag label={`CCC ${c.ccc}`} variant="default" />}
			</div>
		</div>
	);
}

function CloseStage({ c }: StageProps) {
	const f = c.fraud;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<Field label="Outcome" value={f.outcome ?? "Pending"} />
			<div style={{ display: "flex", gap: spacing[6], flexWrap: "wrap" }}>
				<Flag label="SAR / BSA referral" on={f.crossRefs.sarReferral} />
				<Flag label="Card reissue" on={f.crossRefs.cardReissue} />
			</div>
			{f.crossRefs.linkedAccounts.length > 0 && (
				<Field
					label="Linked accounts"
					value={f.crossRefs.linkedAccounts.join(", ")}
				/>
			)}
		</div>
	);
}

const STAGE_COMPONENTS = [
	IntakeStage,
	TriangulateStage,
	DecideStage,
	SuppressBlockStage,
	CloseStage,
];

export default function FraudStepper({ c }: { c: FraudCase }) {
	const lastIndex = FRAUD_STAGES.length - 1;
	const progress = useCaseProgress(c.id, c.currentStage, c.status);
	const [selected, setSelected] = useState(progress.stage);

	const decision = progress.decision;
	const onDecision = (a: HumanAction | null) => setDecisionStore(c.id, a);

	const isActive = selected === progress.stage;
	// Light gating: a disposition is required to advance past Decide.
	const canAdvance = !(selected === DECIDE_INDEX && decision === null);

	const advance = () => {
		const next = Math.min(selected + 1, lastIndex);
		if (next > progress.stage) setStage(c.id, next);
		setSelected(next);
	};

	const StageComponent = STAGE_COMPONENTS[selected] ?? CloseStage;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			<Stepper
				stages={FRAUD_STAGES}
				currentStage={progress.stage}
				selected={selected}
				onSelect={setSelected}
			/>
			<SectionCard
				title={FRAUD_STAGES[selected]}
				accessory={<ProvenanceBadge provenance={FRAUD_PROVENANCE[selected]} />}
			>
				<StageComponent c={c} decision={decision} onDecision={onDecision} />
				<StageFooter
					stage={selected}
					lastIndex={lastIndex}
					isActive={isActive}
					resolved={progress.resolved}
					canAdvance={canAdvance}
					blockedHint="Record a disposition to continue"
					onBack={() => setSelected(Math.max(selected - 1, 0))}
					onAdvance={advance}
					onResolve={() => resolveCase(c.id, fraudOutcome(decision))}
				/>
			</SectionCard>
		</div>
	);
}
