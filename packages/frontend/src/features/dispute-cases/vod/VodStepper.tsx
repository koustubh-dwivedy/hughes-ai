import { useState } from "react";
import { colors, spacing, typography } from "../../../theme/tokens";
import Button from "../../../ui/primitives/Button";
import Tag from "../../../ui/primitives/Tag";
import StageFooter from "../StageFooter";
import Stepper from "../Stepper";
import IntakeExtractionPanel from "../ai/IntakeExtractionPanel";
import ProvenanceBadge from "../ai/ProvenanceBadge";
import { VOD_PROVENANCE } from "../ai/aiTypes";
import { Field, FieldGrid, Flag, SectionCard } from "../caseUi";
import { getCaseAi } from "../data/aiInvestigations";
import {
	resolveCase,
	setStage,
	useCaseProgress,
} from "../data/caseProgressStore";
import { formatDate } from "../format";
import { VOD_STAGES, type VodCase } from "../types";
import RegFLetterPreview from "./RegFLetterPreview";

const TRIAGE_INDEX = 1; // gating point: dispute must be written + timely

function IntakeStage({ c }: { c: VodCase }) {
	const ai = getCaseAi(c.id);
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			{ai?.intake && <IntakeExtractionPanel extraction={ai.intake} />}
			<FieldGrid>
				<Field label="Channel" value={c.channel} />
				<Field label="Received" value={formatDate(c.receivedDate)} />
				<Field label="ACDV #" value={c.acdvNumber ?? "—"} />
			</FieldGrid>
		</div>
	);
}

function VerifyStage({ c }: { c: VodCase }) {
	const v = c.vod;
	return (
		<div style={{ display: "flex", gap: spacing[6], flexWrap: "wrap" }}>
			<Flag label="Written request received" on={v.writtenRequest} />
			<Flag label="Within 30-day window" on={v.withinThirtyDays} />
			<Flag label="Collection hold active" on={v.collectionHold} />
		</div>
	);
}

function AssembleStage({ c }: { c: VodCase }) {
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

function MailStage({ c }: { c: VodCase }) {
	const v = c.vod;
	return (
		<FieldGrid>
			<Field label="Verification mailed" value={v.mailed ? "Yes" : "Pending"} />
			<Field label="Mailed date" value={v.mailedDate ?? "—"} />
			<Field label="Method" value={v.mailedMethod ?? "—"} />
		</FieldGrid>
	);
}

function ReportStage({ c }: { c: VodCase }) {
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

function CloseStage({ c }: { c: VodCase }) {
	const v = c.vod;
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
					<span
						style={{ fontSize: typography.size.sm, color: colors.slate[600] }}
					>
						AI recommends: <strong>{qa.recommendationLabel}</strong>. Resolve
						the case below to finalize.
					</span>
				</div>
			)}
			<Field label="Outcome" value={v.outcome ?? "Pending"} />
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

export default function VodStepper({ c }: { c: VodCase }) {
	const lastIndex = VOD_STAGES.length - 1;
	const progress = useCaseProgress(c.id, c.currentStage, c.status);
	const [selected, setSelected] = useState(progress.stage);

	const isActive = selected === progress.stage;
	// Light gating: a written, timely dispute is required to advance past Triage.
	const timely = c.vod.writtenRequest && c.vod.withinThirtyDays;
	const canAdvance = !(selected === TRIAGE_INDEX && !timely);

	const advance = () => {
		const next = Math.min(selected + 1, lastIndex);
		if (next > progress.stage) setStage(c.id, next);
		setSelected(next);
	};

	const StageComponent = STAGE_COMPONENTS[selected] ?? CloseStage;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[5] }}>
			<Stepper
				stages={VOD_STAGES}
				currentStage={progress.stage}
				selected={selected}
				onSelect={setSelected}
			/>
			<SectionCard
				title={VOD_STAGES[selected]}
				accessory={<ProvenanceBadge provenance={VOD_PROVENANCE[selected]} />}
			>
				<StageComponent c={c} />
				<StageFooter
					stage={selected}
					lastIndex={lastIndex}
					isActive={isActive}
					resolved={progress.resolved}
					canAdvance={canAdvance}
					blockedHint="Confirm a written, timely dispute to continue"
					onBack={() => setSelected(Math.max(selected - 1, 0))}
					onAdvance={advance}
					onResolve={() => resolveCase(c.id, c.vod.outcome ?? "Validated")}
				/>
			</SectionCard>
		</div>
	);
}
