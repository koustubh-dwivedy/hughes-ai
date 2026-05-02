import { Tabs } from "@mantine/core";
import { useSearchParams } from "react-router-dom";
import Combo from "../../charts/Combo";
import Donut from "../../charts/Donut";
import StackedBar from "../../charts/StackedBar";
import Waterfall from "../../charts/Waterfall";
import { getOfficerBranch } from "../../shared/api/api";
import type { OfficerBranchData } from "../../shared/api/dashboardApi";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { useDashboard } from "../../shared/hooks/useDashboard";
import { emit } from "../../shared/telemetry/client";
import { formatCurrency } from "../../shared/utils/format";
import { colors, spacing, typography } from "../../theme/tokens";
import Banner from "../../ui/primitives/Banner";
import ChartCard from "../../ui/primitives/ChartCard";
import DataTable from "../../ui/primitives/DataTable";
import DateBadge from "../../ui/primitives/DateBadge";
import KpiTile from "../../ui/primitives/KpiTile";
import PageHeader from "../../ui/primitives/PageHeader";
import WatchlistTrend from "./WatchlistTrend";
import {
	buildBorrowerRows,
	buildComboData,
	buildSingleLoan,
	buildTabRows,
	buildWaterfallData,
	productLabel,
} from "./chartBuilders";

export { buildBorrowerRows, buildTabRows };

const LOADING_KEYS = ["a", "b", "c"];

const BRANCH_OPTIONS = [
	{ value: "", label: "All Branches" },
	{ value: "1", label: "Main Branch" },
	{ value: "2", label: "East Branch" },
	{ value: "3", label: "West Branch" },
];

const OFFICER_OPTIONS = [
	{ value: "", label: "All Officers" },
	{ value: "off-01", label: "Officer #01" },
	{ value: "off-02", label: "Officer #02" },
	{ value: "off-03", label: "Officer #03" },
];

const gridStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "1fr 1fr",
	gap: spacing[6],
	marginBottom: spacing[6],
};

const labelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	color: colors.slate[600],
	display: "block",
	marginBottom: spacing[1],
};

type SetParams = ReturnType<typeof useSearchParams>[1];

function applyTabChange(value: string | null, set: SetParams) {
	if (!value) return;
	set((prev) => {
		prev.set("tab", value);
		return prev;
	});
	emit({ type: "tab.switched", tab_id: value, panel_id: "officer-branch" });
}

function applyFilterChange(value: string, key: string, set: SetParams) {
	set((prev) => {
		if (value) prev.set(key, value);
		else prev.delete(key);
		return prev;
	});
	emit({ type: "filter.changed", filter_name: key, value });
}

interface KpiTileSpec {
	label: string;
	value: string;
}

function buildKpiTiles(d: OfficerBranchData | null): KpiTileSpec[] {
	if (!d) return [];
	return [
		{ label: "Total Loans", value: formatCurrency(d.total_loans) },
		{ label: "Account Count", value: d.account_count.toLocaleString() },
		{ label: "Avg Loan Balance", value: formatCurrency(d.avg_loan_balance) },
	];
}

export function buildLoanMix(data: OfficerBranchData | null) {
	if (!data) return [];
	return data.loan_mix_donut.map((d) => ({
		label: productLabel(d.product),
		value: d.balance,
	}));
}

function KpiRow({
	tiles,
	loading,
}: { tiles: KpiTileSpec[]; loading: boolean }) {
	return (
		<div
			style={{
				display: "flex",
				gap: spacing[4],
				flexWrap: "wrap" as const,
				marginBottom: spacing[6],
			}}
		>
			{loading
				? LOADING_KEYS.map((k) => <KpiTile key={k} label="" value="" loading />)
				: tiles.map((props) => <KpiTile key={props.label} {...props} />)}
		</div>
	);
}

function FiltersRow({
	branchId,
	officerId,
	setSearchParams,
}: {
	branchId: string;
	officerId: string;
	setSearchParams: SetParams;
}) {
	function onBranch(e: React.ChangeEvent<HTMLSelectElement>) {
		applyFilterChange(e.target.value, "branch_id", setSearchParams);
	}
	function onOfficer(e: React.ChangeEvent<HTMLSelectElement>) {
		applyFilterChange(e.target.value, "officer_id", setSearchParams);
	}
	return (
		<div style={{ display: "flex", gap: spacing[4], marginBottom: spacing[6] }}>
			<label>
				<span style={labelStyle}>Branch</span>
				<select aria-label="Branch filter" value={branchId} onChange={onBranch}>
					{BRANCH_OPTIONS.map((o) => (
						<option key={o.value} value={o.value}>
							{o.label}
						</option>
					))}
				</select>
			</label>
			<label>
				<span style={labelStyle}>Officer</span>
				<select
					aria-label="Officer filter"
					value={officerId}
					onChange={onOfficer}
				>
					{OFFICER_OPTIONS.map((o) => (
						<option key={o.value} value={o.value}>
							{o.label}
						</option>
					))}
				</select>
			</label>
		</div>
	);
}

export default function OfficerBranch() {
	const { asOfDate } = useDashboardContext();
	const [searchParams, setSearchParams] = useSearchParams();
	const tab = searchParams.get("tab");
	const branchId = searchParams.get("branch_id") ?? "";
	const officerId = searchParams.get("officer_id") ?? "";

	const { data, loading, error } = useDashboard(getOfficerBranch, {
		asOfDate,
		tab: tab ?? undefined,
		branchId: branchId ? Number(branchId) : undefined,
		officerId: officerId || undefined,
	});

	if (error) return <p role="alert">Failed to load Officer/Branch data.</p>;

	return (
		<div>
			<PageHeader
				title="Officer / Branch Loans"
				eyebrow="Loan Portfolio"
				dateBadge={asOfDate ? <DateBadge asOfDate={asOfDate} /> : undefined}
			/>
			<Banner message="Demo data only — borrower names are synthetic and do not represent real members." />

			<KpiRow tiles={buildKpiTiles(data)} loading={loading} />
			<FiltersRow
				branchId={branchId}
				officerId={officerId}
				setSearchParams={setSearchParams}
			/>

			<Tabs
				value={tab ?? "new"}
				onChange={(v) => applyTabChange(v, setSearchParams)}
				style={{ marginBottom: spacing[6] }}
			>
				<Tabs.List>
					<Tabs.Tab value="new">New</Tabs.Tab>
					<Tabs.Tab value="renewed">Renewed</Tabs.Tab>
					<Tabs.Tab value="paid_off">Paid Off</Tabs.Tab>
				</Tabs.List>
			</Tabs>

			<div style={gridStyle}>
				<ChartCard title="Loan Mix" loading={loading}>
					<Donut data={buildLoanMix(data)} loading={loading} />
				</ChartCard>
				<ChartCard title="Single-Loan Customers by Type" loading={loading}>
					<StackedBar
						data={buildSingleLoan(data)}
						series={[{ key: "count" }]}
						loading={loading}
					/>
				</ChartCard>
				<ChartCard title="MTD Change by Type ($M)" loading={loading}>
					<Waterfall data={buildWaterfallData(data)} loading={loading} />
				</ChartCard>
				<ChartCard title="Balance vs. Rate" loading={loading}>
					<Combo
						data={buildComboData(data)}
						barLabel="Balance ($M)"
						lineLabel="Rate (%)"
						loading={loading}
					/>
				</ChartCard>
			</div>

			{data?.tab_data && (
				<ChartCard title="Lifecycle" loading={loading}>
					<DataTable
						columns={["Period", "Product Type", "Count", "Amount"]}
						rows={buildTabRows(data)}
						loading={loading}
					/>
				</ChartCard>
			)}

			<WatchlistTrend data={data?.watchlist_trend ?? []} />

			<ChartCard title="Top Borrowers" loading={loading}>
				<DataTable
					columns={["Member", "Balance", "Share %"]}
					rows={buildBorrowerRows(data)}
					loading={loading}
				/>
			</ChartCard>
		</div>
	);
}
