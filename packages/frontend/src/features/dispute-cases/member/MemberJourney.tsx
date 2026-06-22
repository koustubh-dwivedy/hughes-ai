import {
	AlertTriangle,
	ArrowLeftRight,
	AtSign,
	Banknote,
	Building2,
	CreditCard,
	DollarSign,
	FileText,
	FileWarning,
	IdCard,
	Mail,
	MessageSquare,
	MessageSquareWarning,
	Phone,
	Send,
	ShieldAlert,
	UserPlus,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import PageHeader from "../../../ui/primitives/PageHeader";
import Tag from "../../../ui/primitives/Tag";
import BackToQueue from "../BackToQueue";
import EvidenceReferenceChip from "../ai/EvidenceReferenceChip";
import { formatDate } from "../format";
import { getMemberByNumber } from "../mockData";
import JourneyFilters from "./JourneyFilters";
import { getMemberJourney } from "./journeyData";
import { type JourneyFilterState, filterTouchpoints } from "./journeyFilter";
import type { ComplaintTier, Touchpoint, TouchpointType } from "./journeyTypes";

const TYPE_ICON: Record<TouchpointType, React.ReactNode> = {
	complaint: <MessageSquareWarning size={16} />,
	letter: <Mail size={16} />,
	call: <Phone size={16} />,
	message: <MessageSquare size={16} />,
	email: <AtSign size={16} />,
	branch: <Building2 size={16} />,
	transaction: <ArrowLeftRight size={16} />,
	card: <CreditCard size={16} />,
	fee: <DollarSign size={16} />,
	payment: <Banknote size={16} />,
	membership: <UserPlus size={16} />,
	kyc: <IdCard size={16} />,
	application: <FileText size={16} />,
	delinquency: <AlertTriangle size={16} />,
	furnishing: <Send size={16} />,
	dispute: <FileWarning size={16} />,
	fraud: <ShieldAlert size={16} />,
};

const TIER_VARIANT: Record<ComplaintTier, "info" | "warning" | "danger"> = {
	T1: "info",
	T2: "warning",
	T3: "danger",
};

function TouchpointRow({
	t,
	memberName,
}: { t: Touchpoint; memberName?: string }) {
	return (
		<li style={{ display: "flex", gap: spacing[4] }}>
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					alignItems: "center",
					gap: spacing[1],
				}}
			>
				<span
					style={{
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						width: 32,
						height: 32,
						borderRadius: "9999px",
						backgroundColor: colors.slate[100],
						color: colors.slate[700],
						flexShrink: 0,
					}}
				>
					{TYPE_ICON[t.type]}
				</span>
				<span
					style={{ flex: 1, width: 1, backgroundColor: colors.slate[200] }}
				/>
			</div>
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					gap: spacing[1],
					paddingBottom: spacing[5],
				}}
			>
				<div
					style={{
						display: "flex",
						gap: spacing[2],
						alignItems: "center",
						flexWrap: "wrap",
					}}
				>
					<span
						style={{ fontSize: typography.size.xs, color: colors.slate[500] }}
					>
						{formatDate(t.date)}
					</span>
					{t.tier && (
						<Tag label={`${t.tier} complaint`} variant={TIER_VARIANT[t.tier]} />
					)}
					{t.channel && <Tag label={t.channel} variant="default" />}
				</div>
				<span
					style={{ fontSize: typography.size.sm, color: colors.slate[800] }}
				>
					{t.summary}
				</span>
				{t.reference && (
					<EvidenceReferenceChip
						reference={t.reference}
						context={{ memberName, date: t.date }}
					/>
				)}
			</div>
		</li>
	);
}

const INITIAL_FILTER: JourneyFilterState = {
	query: "",
	category: "all",
};

export default function MemberJourney() {
	const { memberNumber } = useParams();
	const member = memberNumber ? getMemberByNumber(memberNumber) : undefined;
	const [filter, setFilter] = useState<JourneyFilterState>(INITIAL_FILTER);

	const all = useMemo(
		() => (memberNumber ? getMemberJourney(memberNumber) : []),
		[memberNumber],
	);
	const filtered = useMemo(() => filterTouchpoints(all, filter), [all, filter]);

	return (
		<div style={{ display: "flex", flexDirection: "column" }}>
			<BackToQueue />
			<PageHeader
				eyebrow="Dispute Center · Member 360"
				title={member ? member.name : `Member ${memberNumber}`}
				subtitle="Full relationship timeline — complaints, contacts, money movement, and account lifecycle."
			/>
			<div style={{ marginBottom: spacing[5] }}>
				<JourneyFilters
					state={filter}
					onChange={setFilter}
					count={filtered.length}
					total={all.length}
				/>
			</div>
			<ol
				style={{
					listStyle: "none",
					margin: 0,
					padding: spacing[6],
					border: `1px solid ${colors.slate[200]}`,
					borderRadius: radii.xl,
					backgroundColor: colors.white,
				}}
			>
				{filtered.map((t) => (
					<TouchpointRow
						key={`${t.date}-${t.type}-${t.summary}`}
						t={t}
						memberName={member?.name}
					/>
				))}
				{filtered.length === 0 && (
					<li
						style={{ color: colors.slate[500], fontSize: typography.size.sm }}
					>
						No touchpoints match your filters.
					</li>
				)}
			</ol>
		</div>
	);
}
