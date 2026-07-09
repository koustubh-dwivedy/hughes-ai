import { ArrowUpRight } from "lucide-react";
import { useParams } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import Banner from "../../ui/primitives/Banner";
import PageHeader from "../../ui/primitives/PageHeader";
import Tag from "../../ui/primitives/Tag";
import AcdvAttachmentsPanel from "./AcdvAttachmentsPanel";
import BackToQueue from "./BackToQueue";
import type { AssetContext } from "./assets/assetContent";
import { Field, FieldGrid, SectionCard } from "./caseUi";
import DataAccuracyStepper from "./data-accuracy/DataAccuracyStepper";
import { useCaseProgress } from "./data/caseProgressStore";
import { getInitialSignoffs } from "./data/caseSignoffs";
import { formatCurrency, formatDate, slaLabel, slaVariant } from "./format";
import FraudStepper from "./fraud/FraudStepper";
import { getCaseById } from "./mockData";
import {
	type DisputeCase,
	REASON_CODE_LABEL,
	categoryForReason,
} from "./types";

/** The ACDV reason code a case carries (data-accuracy detail or fraud detail). */
function caseReasonCode(c: DisputeCase): string | null {
	if (c.type === "DATA_ACCURACY") return c.dataAccuracy.reasonCode;
	if (c.type === "FRAUD") return c.fraud.reasonCode;
	return null;
}

function CaseHeaderMeta({ c }: { c: DisputeCase }) {
	return (
		<div
			style={{
				display: "flex",
				gap: spacing[2],
				alignItems: "center",
				flexWrap: "wrap",
			}}
		>
			{caseReasonCode(c) && (
				<>
					<Tag
						label={categoryForReason(caseReasonCode(c) as string)}
						variant={c.type === "FRAUD" ? "danger" : "info"}
					/>
					<Tag
						label={`Reason ${caseReasonCode(c)} — ${REASON_CODE_LABEL[caseReasonCode(c) as keyof typeof REASON_CODE_LABEL]}`}
						variant="default"
					/>
				</>
			)}
			<Tag
				label={`SLA ${slaLabel(c.slaDueDate)}`}
				variant={slaVariant(c.slaDueDate)}
			/>
			<Tag label={`CCC ${c.ccc ?? "—"}`} variant="info" />
			<span style={{ fontSize: typography.size.sm, color: colors.slate[500] }}>
				ACDV {c.acdvNumber ?? "—"} · {c.assignee}
			</span>
		</div>
	);
}

function SummaryPanels({ c }: { c: DisputeCase }) {
	const a = c.subjectAccount;
	return (
		<div
			style={{
				display: "grid",
				gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
				gap: spacing[5],
			}}
		>
			<SectionCard
				title="Member"
				accessory={
					<a
						href={`/disputes/member/${c.member.memberNumber}`}
						target="_blank"
						rel="noopener noreferrer"
						style={{
							display: "inline-flex",
							alignItems: "center",
							gap: spacing[1],
							padding: `${spacing[1]} ${spacing[3]}`,
							borderRadius: radii.md,
							backgroundColor: colors.slate[800],
							color: colors.white,
							fontSize: typography.size.sm,
							fontWeight: typography.weight.semibold,
							textDecoration: "none",
						}}
					>
						View customer journey <ArrowUpRight size={14} />
					</a>
				}
			>
				<FieldGrid>
					<Field label="Name" value={c.member.name} />
					<Field label="Member #" value={c.member.memberNumber} />
					<Field label="SSN" value={c.member.ssnMasked} />
					<Field label="Phone" value={c.member.phone} />
				</FieldGrid>
			</SectionCard>
			<SectionCard title="Subject account (as furnished)">
				<FieldGrid>
					<Field label="Account" value={a.accountNumberMasked} source="core" />
					<Field label="Product" value={a.productType} source="LOS" />
					<Field
						label="Current balance"
						value={formatCurrency(a.currentBalance)}
						source="core"
					/>
					<Field label="Status" value={a.accountStatus} source="core" />
					<Field
						label="DOFD"
						value={a.dofd ? formatDate(a.dofd) : "—"}
						source="core"
					/>
					<Field
						label="Bureaus"
						value={a.reportedBureaus.join(", ")}
						source="core"
					/>
				</FieldGrid>
			</SectionCard>
		</div>
	);
}

function caseOutcome(c: DisputeCase): string | null {
	return c.type === "FRAUD" ? c.fraud.outcome : c.dataAccuracy.outcome;
}

function stepperFor(c: DisputeCase) {
	return c.type === "FRAUD" ? (
		<FraudStepper c={c} />
	) : (
		<DataAccuracyStepper c={c} />
	);
}

function CaseFileContent({ c }: { c: DisputeCase }) {
	const progress = useCaseProgress(
		c.id,
		c.currentStage,
		c.status,
		getInitialSignoffs(c.id),
	);
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[6] }}>
			<div style={{ display: "flex", flexDirection: "column" }}>
				<BackToQueue />
				<PageHeader
					eyebrow={`Dispute Center · ${c.id}`}
					title={`${c.member.name} — ${progress.status}`}
				/>
			</div>
			{progress.resolved && (
				<Banner
					message={`Case resolved — ${progress.outcome ?? caseOutcome(c) ?? "closed"}`}
				/>
			)}
			<CaseHeaderMeta c={c} />
			<SummaryPanels c={c} />
			{c.attachments.length > 0 && (
				<AcdvAttachmentsPanel
					caseId={c.id}
					attachments={c.attachments}
					context={attachmentContext(c)}
				/>
			)}
			{stepperFor(c)}
		</div>
	);
}

function attachmentContext(c: DisputeCase): AssetContext {
	return {
		memberName: c.member.name,
		memberAddress: c.member.address,
		date: c.receivedDate,
		accountRef: c.subjectAccount.accountNumberMasked,
	};
}

export default function CaseFile() {
	const { caseId } = useParams();
	const c = caseId ? getCaseById(caseId) : undefined;

	if (!c) {
		return (
			<div style={{ display: "flex", flexDirection: "column" }}>
				<BackToQueue />
				<PageHeader eyebrow="Dispute Center" title="Case not found" />
				<p style={{ color: colors.slate[500] }}>No case matches “{caseId}”.</p>
			</div>
		);
	}

	return <CaseFileContent c={c} />;
}
