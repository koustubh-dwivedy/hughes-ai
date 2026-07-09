import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import StageFooter from "../StageFooter";
import StageLayout from "../StageLayout";
import ApprovalGate from "../ai/ApprovalGate";
import IntakeExtractionPanel from "../ai/IntakeExtractionPanel";
import ProvenanceBadge from "../ai/ProvenanceBadge";
import ReasoningTrace from "../ai/ReasoningTrace";
import { DATA_ACCURACY_PROVENANCE } from "../ai/aiTypes";
import type { AssetContext } from "../assets/assetContent";
import { Field, FieldGrid } from "../caseUi";
import { REASON_CODE_LABEL, RESPONSE_CODE_LABEL, daOutcome } from "../codes";
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
import { DATA_ACCURACY_STAGES, type DataAccuracyCase } from "../types";
import AutonomyGatePanel from "./AutonomyGatePanel";
import FieldComparisonPanel from "./FieldComparisonPanel";

const DECIDE_INDEX = 2;
const EMPTY: Signoff = { option: "", comments: "" };

const DECIDE_OPTIONS = [
	{ value: "approve", label: "Approve" },
	{ value: "override", label: "Override" },
	{ value: "more_info", label: "Request more info" },
];

function reasonLabel(c: DataAccuracyCase): string {
	const da = c.dataAccuracy;
	return `${da.reasonCode} — ${REASON_CODE_LABEL[da.reasonCode]}`;
}

function FreeTextCallout({ text }: { text: string }) {
	return (
		<div
			style={{
				padding: spacing[4],
				borderRadius: radii.lg,
				border: "1px solid #fde68a",
				backgroundColor: "#fffbeb",
				fontSize: typography.size.sm,
				color: "#854d0e",
			}}
		>
			<strong>FCRA Relevant Information (free-text):</strong> “{text}”
		</div>
	);
}

function SuccessNote({ text }: { text: string }) {
	return (
		<div
			role="note"
			style={{
				padding: `${spacing[3]} ${spacing[4]}`,
				borderRadius: radii.lg,
				border: "1px solid #bbf7d0",
				backgroundColor: "#f0fdf4",
				color: "#166534",
				fontSize: typography.size.sm,
				fontWeight: typography.weight.medium,
			}}
		>
			{text}
		</div>
	);
}

interface StageProps {
	c: DataAccuracyCase;
	signoffs: Record<number, Signoff>;
	onSignoff: (index: number, s: Signoff) => void;
}

function IntakeStage({ c }: StageProps) {
	const ai = getCaseAi(c.id);
	const da = c.dataAccuracy;
	const ctx: AssetContext = {
		memberName: c.member.name,
		memberAddress: c.member.address,
		date: c.receivedDate,
		accountRef: c.subjectAccount.accountNumberMasked,
		disputeCode: reasonLabel(c),
		disputeStatement:
			da.freeText ??
			`${c.member.name} disputes ${REASON_CODE_LABEL[da.reasonCode].toLowerCase()}.`,
	};
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			{ai?.intake && (
				<IntakeExtractionPanel extraction={ai.intake} context={ctx} />
			)}
			<FieldGrid>
				<Field label="Channel" value={c.channel} />
				<Field label="Reason code" value={reasonLabel(c)} />
				<Field label="ACDV #" value={c.acdvNumber ?? "—"} />
			</FieldGrid>
		</div>
	);
}

function CompareStage({ c }: StageProps) {
	const da = c.dataAccuracy;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			<FieldComparisonPanel
				fields={da.disputedFields}
				dateOfAccountInfo={da.dateOfAccountInfo}
			/>
			{da.freeText && <FreeTextCallout text={da.freeText} />}
		</div>
	);
}

function SectionHeading({ text }: { text: string }) {
	return (
		<span
			style={{
				fontSize: typography.size.xs,
				fontWeight: typography.weight.semibold,
				textTransform: "uppercase",
				letterSpacing: "0.04em",
				color: colors.slate[500],
			}}
		>
			{text}
		</span>
	);
}

function DecideStage({ c, signoffs, onSignoff }: StageProps) {
	const inv = getCaseAi(c.id)?.investigation;
	const da = c.dataAccuracy;
	const autonomous = da.autonomyMode === "autonomous";
	const hasImage = c.attachments.some((a) => !a.acknowledged);
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			{inv && (
				<AutonomyGatePanel
					checks={inv.deterministicChecks}
					recommendedResponse={da.recommendedResponse}
					autonomyMode={da.autonomyMode}
				/>
			)}
			{inv?.reasoning && inv.reasoning.length > 0 && (
				<div
					style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}
				>
					<SectionHeading text="How the agent reasoned" />
					<ReasoningTrace steps={inv.reasoning} />
				</div>
			)}
			{autonomous ? (
				<SuccessNote text="✓ Auto-resolved — all three gates passed. No human sign-off required; the corrected value is refurnished and audit-logged." />
			) : (
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						gap: spacing[3],
					}}
				>
					{/* Everything the reviewer needs to decide, in one screen. */}
					<SectionHeading text="Evidence for your decision" />
					<FieldComparisonPanel
						fields={da.disputedFields}
						dateOfAccountInfo={da.dateOfAccountInfo}
					/>
					{da.freeText && <FreeTextCallout text={da.freeText} />}
					{hasImage && (
						<span
							style={{ fontSize: typography.size.sm, color: colors.slate[600] }}
						>
							📎 Consumer image(s) attached — review them in the “ACDV
							attachments” panel above before signing off.
						</span>
					)}
					<ApprovalGate
						title="Sign off on the AI recommendation"
						recommendationLabel={inv?.recommendationLabel}
						options={DECIDE_OPTIONS}
						value={signoffs[DECIDE_INDEX] ?? EMPTY}
						onChange={(v) => onSignoff(DECIDE_INDEX, v)}
					/>
				</div>
			)}
		</div>
	);
}

function ReportStage({ c }: StageProps) {
	const da = c.dataAccuracy;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<div style={{ display: "flex", gap: spacing[3], alignItems: "center" }}>
				<span>Metro 2 reporting:</span>
				<Tag label={`CCC ${c.ccc ?? "—"}`} variant="info" />
				<span>→ on resolution</span>
				<Tag label="XH (clears XB)" variant="success" />
			</div>
			<Field
				label="e-OSCAR response"
				value={`${da.recommendedResponse} — ${RESPONSE_CODE_LABEL[da.recommendedResponse]}`}
			/>
		</div>
	);
}

function CloseStage({ c }: StageProps) {
	const da = c.dataAccuracy;
	return (
		<FieldGrid>
			<Field
				label="Response code"
				value={`${da.recommendedResponse} — ${RESPONSE_CODE_LABEL[da.recommendedResponse]}`}
			/>
			<Field label="Outcome" value={da.outcome ?? "Pending"} />
		</FieldGrid>
	);
}

const STAGE_COMPONENTS = [
	IntakeStage,
	CompareStage,
	DecideStage,
	ReportStage,
	CloseStage,
];

function requiresSignoff(c: DataAccuracyCase, stage: number): boolean {
	return (
		stage === DECIDE_INDEX && c.dataAccuracy.autonomyMode === "draft_for_human"
	);
}

export default function DataAccuracyStepper({ c }: { c: DataAccuracyCase }) {
	const lastIndex = DATA_ACCURACY_STAGES.length - 1;
	const progress = useCaseProgress(
		c.id,
		c.currentStage,
		c.status,
		getInitialSignoffs(c.id),
	);
	const [selected, setSelected] = useState(progress.stage);
	const onSignoff = (i: number, s: Signoff) => setSignoff(c.id, i, s);

	const isActive = selected === progress.stage;
	const draft = c.dataAccuracy.autonomyMode === "draft_for_human";
	const atDecide = selected === DECIDE_INDEX;
	const pending = c.attachments.filter(
		(a) => !a.acknowledged && !progress.acknowledged.includes(a.fileName),
	);
	const signoffOk =
		!requiresSignoff(c, selected) ||
		signoffComplete(progress.signoffs[selected]);
	const attachmentsOk = !atDecide || pending.length === 0;
	const canAdvance = signoffOk && attachmentsOk;

	const advance = () => {
		const next = Math.min(selected + 1, lastIndex);
		if (next > progress.stage) setStage(c.id, next);
		setSelected(next);
	};

	const StageComponent = STAGE_COMPONENTS[selected] ?? CloseStage;
	const blockedHint =
		atDecide && pending.length > 0
			? "View the attached consumer image to continue"
			: draft
				? "Select an option and add notes to continue"
				: "";

	return (
		<StageLayout
			stages={DATA_ACCURACY_STAGES}
			currentStage={progress.stage}
			selected={selected}
			onSelect={setSelected}
			title={DATA_ACCURACY_STAGES[selected]}
			accessory={
				<ProvenanceBadge provenance={DATA_ACCURACY_PROVENANCE[selected]} />
			}
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
				blockedHint={blockedHint}
				onBack={() => setSelected(Math.max(selected - 1, 0))}
				onAdvance={advance}
				onResolve={() =>
					resolveCase(
						c.id,
						daOutcome(
							c.dataAccuracy.recommendedResponse,
							progress.signoffs[DECIDE_INDEX]?.option,
						),
					)
				}
			/>
		</StageLayout>
	);
}
