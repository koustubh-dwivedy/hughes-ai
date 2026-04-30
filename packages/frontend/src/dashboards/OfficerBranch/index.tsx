import { useSearchParams } from "react-router-dom";
import Combo from "../../charts/Combo";
import DataTable from "../../charts/DataTable";
import Donut from "../../charts/Donut";
import KpiTile from "../../charts/KpiTile";
import StackedBar from "../../charts/StackedBar";
import Waterfall from "../../charts/Waterfall";
import Banner from "../../components/Banner";
import { useDashboardContext } from "../../context/DashboardContext";
import { useDashboard } from "../../hooks/useDashboard";
import DashboardShell from "../../layout/DashboardShell";
import { getOfficerBranch } from "../../lib/api";
import type { OfficerBranchData } from "../../lib/dashboardApi";
import { spacing } from "../../theme/tokens";
import Tabs from "./Tabs";
import WatchlistTrend from "./WatchlistTrend";

function fmt(n: number): string {
	return `$${(n / 1_000_000).toFixed(1)}M`;
}

function buildKpiTiles(data: OfficerBranchData | null) {
	if (!data) {
		return [
			{ label: "Total Loans", value: "$0.0M" },
			{ label: "Account Count", value: "0" },
			{ label: "Avg Loan Balance", value: "$0.0M" },
		];
	}
	return [
		{ label: "Total Loans", value: fmt(data.total_loans) },
		{ label: "Account Count", value: data.account_count.toLocaleString() },
		{ label: "Avg Loan Balance", value: fmt(data.avg_loan_balance) },
	];
}

export function buildLoanMix(data: OfficerBranchData | null) {
	if (!data) return [];
	return data.loan_mix_donut.map((d) => ({
		label: d.product,
		value: d.balance,
	}));
}

function buildWaterfall(data: OfficerBranchData | null) {
	if (!data) return [];
	return data.change_by_type_waterfall.map((d) => ({
		label: d.product,
		value: d.delta,
	}));
}

function buildSingleLoanBar(data: OfficerBranchData | null) {
	if (!data) return [];
	return data.single_loan_customers_by_type.map((d) => ({
		period: d.product,
		count: d.count,
	}));
}

function buildComboData(data: OfficerBranchData | null) {
	if (!data) return [];
	return data.combo_balance_rate.map((d) => ({
		period: d.product,
		bar: d.balance / 1_000_000,
		line: d.weighted_avg_rate * 100,
	}));
}

export function buildBorrowerRows(
	data: OfficerBranchData | null,
): Record<string, unknown>[] {
	if (!data) return [];
	return data.top_25_borrowers.map((d) => ({
		Member: d.member_name,
		Balance: fmt(d.balance),
		"Share %": `${d.share_pct.toFixed(1)}%`,
	}));
}

export function buildTabRows(
	data: OfficerBranchData | null,
): Record<string, unknown>[] {
	if (!data?.tab_data) return [];
	return data.tab_data.map((r) => ({
		Period: r.period,
		"Product Type": r.product_type,
		Count: r.count.toLocaleString(),
		Amount: fmt(r.amount),
	}));
}

export default function OfficerBranch() {
	const { asOfDate } = useDashboardContext();
	const [searchParams, setSearchParams] = useSearchParams();
	const tab = searchParams.get("tab");

	const { data, loading, error } = useDashboard(getOfficerBranch, {
		asOfDate,
		tab: tab ?? undefined,
	});

	function onSelectTab(key: string) {
		setSearchParams((prev) => {
			prev.set("tab", key);
			return prev;
		});
	}

	const kpiTiles = buildKpiTiles(data);
	const loanMix = buildLoanMix(data);
	const waterfallData = buildWaterfall(data);
	const singleLoan = buildSingleLoanBar(data);
	const comboData = buildComboData(data);
	const tableRows = buildBorrowerRows(data);

	return (
		<DashboardShell
			title="Officer / Branch Loans"
			loading={loading}
			error={error}
			empty={!loading && !error && !data}
		>
			<Banner message="Demo data only — borrower names are synthetic and do not represent real members." />

			<div
				style={{
					display: "flex",
					gap: spacing[4],
					flexWrap: "wrap",
					marginBottom: spacing[6],
				}}
			>
				{kpiTiles.map((t) => (
					<KpiTile key={t.label} label={t.label} value={t.value} />
				))}
			</div>

			<Tabs active={tab} onSelect={onSelectTab} />

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: spacing[6],
					marginBottom: spacing[6],
				}}
			>
				<Donut data={loanMix} title="Loan Mix" loading={loading} />
				<StackedBar
					data={singleLoan}
					series={[{ key: "count" }]}
					title="Single-Loan Customers by Type"
					loading={loading}
				/>
				<Waterfall
					data={waterfallData}
					title="MTD Change by Type ($M)"
					loading={loading}
				/>
				<Combo
					data={comboData}
					barLabel="Balance ($M)"
					lineLabel="Rate (%)"
					title="Balance vs. Rate"
					loading={loading}
				/>
				{data?.tab_data && (
					<DataTable
						columns={["Period", "Product Type", "Count", "Amount"]}
						rows={buildTabRows(data)}
						loading={loading}
					/>
				)}
			</div>

			<WatchlistTrend data={data?.watchlist_trend ?? []} />

			<DataTable
				columns={["Member", "Balance", "Share %"]}
				rows={tableRows}
				loading={loading}
			/>
		</DashboardShell>
	);
}
