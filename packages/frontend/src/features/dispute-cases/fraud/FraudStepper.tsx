import { useState } from "react";
import { colors, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import StageFooter from "../StageFooter";
import StageLayout from "../StageLayout";
import ApprovalGate from "../ai/ApprovalGate";
import IntakeExtractionPanel from "../ai/IntakeExtractionPanel";
import ProvenanceBadge from "../ai/ProvenanceBadge";
import { FRAUD_PROVENANCE } from "../ai/aiTypes";
import { Field, FieldGrid, Flag, SubSection } from "../caseUi";
import { getCaseAi } from "../data/aiInvestigations";
import {
	type Signoff,
	resolveCase,
	setSignoff,
	setStage,
	signoffComplete,
	useCaseProgress,
} from "../data/caseProgressStore";
import { getInitialSignoffs } from "../data/caseSignoffs";
import { formatDate } from "../format";
import { FRAUD_STAGES, type FraudCase } from "../types";
import InvestigationReview from "./InvestigationReview";

const INTAKE_INDEX = 0;
const DECIDE_INDEX = 1; // merged "Triangulate & decide" stage
const EMPTY: Signoff = { option: "", comments: "" };

const INTAKE_OPTIONS = [
	{ value: "confirm", label: "Confirm AI findings" },
	{ value: "flag", label: "Flag for review" },
];
const DECIDE_OPTIONS = [
	{ value: "approve", label: "Approve" },
	{ value: "override", label: "Override" },
	{ value: "more_info", label: "Request more info" },
];

function fraudOutcome(option: string | undefined): string {
	if (option === "override") return "Denied — first-party (kept furnishing)";
	if (option === "more_info") return "Pending — more information requested";
	return "Blocked & suppressed (§605B)";
}

interface StageProps {
	c: FraudCase;
	signoffs: Record<number, Signoff>;
	onSignoff: (index: number, s: Signoff) => void;
}

function IntakeStage({ c, signoffs, onSignoff }: StageProps) {
	const ai = getCaseAi(c.id);
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			{ai?.intake && <IntakeExtractionPanel extraction={ai.intake} />}
			<FieldGrid>
				<Field label="Channel" value={c.channel} />
				<Field label="Received" value={formatDate(c.receivedDate)} />
				<Field label="Fraud sub-type" value={c.fraud.subType} />
				<Field
					label="Identity Theft Report"
					value={
						c.fraud.identityTheftReport.onFile
							? (c.fraud.identityTheftReport.type ?? "On file")
							: "Not on file"
					}
				/>
			</FieldGrid>
			{ai?.intake && (
				<ApprovalGate
					title="Sign off on the AI intake findings"
					options={INTAKE_OPTIONS}
					value={signoffs[INTAKE_INDEX] ?? EMPTY}
					onChange={(v) => onSignoff(INTAKE_INDEX, v)}
				/>
			)}
		</div>
	);
}

function InvestigateStage({ c, signoffs, onSignoff }: StageProps) {
	const ai = getCaseAi(c.id);
	if (!ai?.investigation) return null;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			<InvestigationReview
				investigation={ai.investigation}
				rows={c.fraud.triangulation}
				memberName={c.member.name}
			/>
			<ApprovalGate
				title="Record your disposition"
				recommendationLabel={ai.investigation.recommendationLabel}
				options={DECIDE_OPTIONS}
				value={signoffs[DECIDE_INDEX] ?? EMPTY}
				onChange={(v) => onSignoff(DECIDE_INDEX, v)}
			/>
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
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
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
			<SubSection title="§605B suppression">
				<Tag label={`§605B clock: ${blockLabel}`} variant={blockVariant} />
				<div style={{ display: "flex", gap: spacing[6], flexWrap: "wrap" }}>
					<Flag label="Furnishing suppressed" on={f.blockApplied} />
					<Flag label="Prevent re-furnishing" on={f.preventRefurnish} />
					<Flag label="Collection prohibited" on={f.collectionProhibition} />
				</div>
			</SubSection>
			<SubSection title="Metro 2 / e-OSCAR">
				<div
					style={{
						display: "flex",
						gap: spacing[3],
						alignItems: "center",
						flexWrap: "wrap",
					}}
				>
					<Tag label="Tradeline suppressed" variant="info" />
					<Tag label="AUD submitted" variant="info" />
					{c.ccc && <Tag label={`CCC ${c.ccc}`} variant="default" />}
				</div>
			</SubSection>
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
	InvestigateStage,
	SuppressBlockStage,
	CloseStage,
];

/** Which fraud stages require a human sign-off (those rendering an AI panel). */
function requiresSignoff(c: FraudCase, stage: number): boolean {
	const ai = getCaseAi(c.id);
	if (stage === INTAKE_INDEX) return Boolean(ai?.intake);
	if (stage === DECIDE_INDEX) return Boolean(ai?.investigation);
	return false;
}

export default function FraudStepper({ c }: { c: FraudCase }) {
	const lastIndex = FRAUD_STAGES.length - 1;
	const progress = useCaseProgress(
		c.id,
		c.currentStage,
		c.status,
		getInitialSignoffs(c.id),
	);
	const [selected, setSelected] = useState(progress.stage);
	const onSignoff = (i: number, s: Signoff) => setSignoff(c.id, i, s);

	const isActive = selected === progress.stage;
	const canAdvance =
		!requiresSignoff(c, selected) ||
		signoffComplete(progress.signoffs[selected]);

	const advance = () => {
		const next = Math.min(selected + 1, lastIndex);
		if (next > progress.stage) setStage(c.id, next);
		setSelected(next);
	};

	const StageComponent = STAGE_COMPONENTS[selected] ?? CloseStage;
	return (
		<StageLayout
			stages={FRAUD_STAGES}
			currentStage={progress.stage}
			selected={selected}
			onSelect={setSelected}
			title={FRAUD_STAGES[selected]}
			accessory={<ProvenanceBadge provenance={FRAUD_PROVENANCE[selected]} />}
		>
			<StageComponent
				c={c}
				signoffs={progress.signoffs}
				onSignoff={onSignoff}
			/>
			<StageFooter
				stage={selected}
				lastIndex={lastIndex}
				isActive={isActive}
				resolved={progress.resolved}
				canAdvance={canAdvance}
				blockedHint="Select an option and add notes to continue"
				onBack={() => setSelected(Math.max(selected - 1, 0))}
				onAdvance={advance}
				onResolve={() =>
					resolveCase(
						c.id,
						fraudOutcome(progress.signoffs[DECIDE_INDEX]?.option),
					)
				}
			/>
		</StageLayout>
	);
}
