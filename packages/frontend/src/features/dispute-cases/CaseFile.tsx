import { ArrowUpRight } from "lucide-react";
import { useParams } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import Banner from "../../ui/primitives/Banner";
import PageHeader from "../../ui/primitives/PageHeader";
import Tag from "../../ui/primitives/Tag";
import BackToQueue from "./BackToQueue";
import { Field, FieldGrid, SectionCard } from "./caseUi";
import { useCaseProgress } from "./data/caseProgressStore";
import { getInitialSignoffs } from "./data/caseSignoffs";
import { formatCurrency, formatDate, slaLabel, slaVariant } from "./format";
import FraudStepper from "./fraud/FraudStepper";
import { getCaseById } from "./mockData";
import type { DisputeCase } from "./types";
import VodStepper from "./vod/VodStepper";

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
			<Tag
				label={c.type === "FRAUD" ? "Fraud" : "VOD"}
				variant={c.type === "FRAUD" ? "danger" : "default"}
			/>
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
	return c.type === "VOD" ? c.vod.outcome : c.fraud.outcome;
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
			{c.type === "VOD" ? <VodStepper c={c} /> : <FraudStepper c={c} />}
		</div>
	);
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
