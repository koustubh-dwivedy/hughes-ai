import { useState } from "react";
import { colors, spacing, typography } from "../../../theme/tokens";
import Button from "../../../ui/primitives/Button";
import Tag from "../../../ui/primitives/Tag";
import StageFooter from "../StageFooter";
import StageLayout from "../StageLayout";
import ApprovalGate from "../ai/ApprovalGate";
import IntakeExtractionPanel from "../ai/IntakeExtractionPanel";
import ProvenanceBadge from "../ai/ProvenanceBadge";
import { VOD_PROVENANCE } from "../ai/aiTypes";
import { Field, FieldGrid, Flag } from "../caseUi";
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
import { VOD_STAGES, type VodCase } from "../types";
import RegFLetterPreview from "./RegFLetterPreview";

const INTAKE_INDEX = 0;
const TRIAGE_INDEX = 1;
const CLOSE_INDEX = 5;
const EMPTY: Signoff = { option: "", comments: "" };

const INTAKE_OPTIONS = [
	{ value: "confirm", label: "Confirm match" },
	{ value: "flag", label: "Flag discrepancy" },
];
const CLOSE_OPTIONS = [
	{ value: "approve", label: "Approve" },
	{ value: "override", label: "Override" },
	{ value: "more_info", label: "Request more info" },
];

function vodOutcome(option: string | undefined): string {
	if (option === "override") return "Unable to validate — tradeline deleted";
	if (option === "more_info") return "Pending — more information requested";
	return "Validated";
}

interface StageProps {
	c: VodCase;
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
				<Field label="ACDV #" value={c.acdvNumber ?? "—"} />
			</FieldGrid>
			{ai?.intake && (
				<ApprovalGate
					title="Sign off on the AI identity match"
					options={INTAKE_OPTIONS}
					value={signoffs[INTAKE_INDEX] ?? EMPTY}
					onChange={(v) => onSignoff(INTAKE_INDEX, v)}
				/>
			)}
		</div>
	);
}

function VerifyStage({ c }: StageProps) {
	const v = c.vod;
	return (
		<div style={{ display: "flex", gap: spacing[6], flexWrap: "wrap" }}>
			<Flag label="Written request received" on={v.writtenRequest} />
			<Flag label="Within 30-day window" on={v.withinThirtyDays} />
			<Flag label="Collection hold active" on={v.collectionHold} />
		</div>
	);
}

function AssembleStage({ c }: StageProps) {
	const v = c.vod;
	const [showLetter, setShowLetter] = useState(false);
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<span>Verification package (assembled from LOS + core)</span>
				<Button size="xs" onClick={() => setShowLetter(true)}>
					Generate cover letter
				</Button>
			</div>
			<FieldGrid>
				{v.regFFields.map((f) => (
					<Field
						key={f.label}
						label={f.label}
						value={f.value}
						source={f.source}
					/>
				))}
			</FieldGrid>
			<div style={{ display: "flex", gap: spacing[4], flexWrap: "wrap" }}>
				{v.validationDocs.map((d) => (
					<Tag
						key={d.label}
						label={`${d.label}${d.available ? "" : " (missing)"}`}
						variant={d.available ? "success" : "warning"}
					/>
				))}
			</div>
			{showLetter && (
				<RegFLetterPreview c={c} onClose={() => setShowLetter(false)} />
			)}
		</div>
	);
}

function MailStage({ c }: StageProps) {
	const v = c.vod;
	return (
		<FieldGrid>
			<Field label="Verification mailed" value={v.mailed ? "Yes" : "Pending"} />
			<Field label="Mailed date" value={v.mailedDate ?? "—"} />
			<Field label="Method" value={v.mailedMethod ?? "—"} />
		</FieldGrid>
	);
}

function ReportStage({ c }: StageProps) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<div style={{ display: "flex", gap: spacing[3], alignItems: "center" }}>
				<span>Metro 2 reporting:</span>
				<Tag label={`CCC ${c.ccc ?? "—"}`} variant="info" />
				<span>→ on resolution</span>
				<Tag label="XH (clears XB)" variant="success" />
			</div>
			<Field
				label="ACDV / AUD response"
				value={c.acdvNumber ? "AUD queued" : "Direct response"}
			/>
		</div>
	);
}

function CloseStage({ c, signoffs, onSignoff }: StageProps) {
	const qa = getCaseAi(c.id)?.validationQa;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			{qa && (
				<div
					style={{ display: "flex", flexDirection: "column", gap: spacing[3] }}
				>
					<div style={{ display: "flex", gap: spacing[2], flexWrap: "wrap" }}>
						<Tag label="✨ AI validation QA" variant="info" />
						<Tag
							label={qa.complete ? "Package complete" : "Package incomplete"}
							variant={qa.complete ? "success" : "warning"}
						/>
					</div>
					{qa.discrepancies.length > 0 && (
						<ul
							style={{
								margin: 0,
								paddingLeft: spacing[6],
								fontSize: typography.size.sm,
								color: colors.slate[700],
							}}
						>
							{qa.discrepancies.map((d) => (
								<li key={d}>{d}</li>
							))}
						</ul>
					)}
					<ApprovalGate
						title="Sign off to resolve the dispute"
						recommendationLabel={qa.recommendationLabel}
						options={CLOSE_OPTIONS}
						value={signoffs[CLOSE_INDEX] ?? EMPTY}
						onChange={(v) => onSignoff(CLOSE_INDEX, v)}
					/>
				</div>
			)}
			<Field label="Outcome" value={c.vod.outcome ?? "Pending"} />
		</div>
	);
}

const STAGE_COMPONENTS = [
	IntakeStage,
	VerifyStage,
	AssembleStage,
	MailStage,
	ReportStage,
	CloseStage,
];

function requiresSignoff(c: VodCase, stage: number): boolean {
	const ai = getCaseAi(c.id);
	if (stage === INTAKE_INDEX) return Boolean(ai?.intake);
	if (stage === CLOSE_INDEX) return Boolean(ai?.validationQa);
	return false;
}

export default function VodStepper({ c }: { c: VodCase }) {
	const lastIndex = VOD_STAGES.length - 1;
	const progress = useCaseProgress(
		c.id,
		c.currentStage,
		c.status,
		getInitialSignoffs(c.id),
	);
	const [selected, setSelected] = useState(progress.stage);
	const onSignoff = (i: number, s: Signoff) => setSignoff(c.id, i, s);

	const isActive = selected === progress.stage;
	const timely = c.vod.writtenRequest && c.vod.withinThirtyDays;
	const triageOk = !(selected === TRIAGE_INDEX && !timely);
	const signoffOk =
		!requiresSignoff(c, selected) ||
		signoffComplete(progress.signoffs[selected]);
	const canAdvance = triageOk && signoffOk;

	const advance = () => {
		const next = Math.min(selected + 1, lastIndex);
		if (next > progress.stage) setStage(c.id, next);
		setSelected(next);
	};

	const StageComponent = STAGE_COMPONENTS[selected] ?? CloseStage;
	const blockedHint = requiresSignoff(c, selected)
		? "Select an option and add notes to continue"
		: "Confirm a written, timely dispute to continue";

	return (
		<StageLayout
			stages={VOD_STAGES}
			currentStage={progress.stage}
			selected={selected}
			onSelect={setSelected}
			title={VOD_STAGES[selected]}
			accessory={<ProvenanceBadge provenance={VOD_PROVENANCE[selected]} />}
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
					resolveCase(c.id, vodOutcome(progress.signoffs[CLOSE_INDEX]?.option))
				}
			/>
		</StageLayout>
	);
}
