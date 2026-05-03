import { Tabs } from "@mantine/core";
import { useSearchParams } from "react-router-dom";
import Combo from "../../charts/Combo";
import Donut from "../../charts/Donut";
import Waterfall from "../../charts/Waterfall";
import type { OfficerBranchData } from "../../shared/api/dashboardApi";
import DashboardHeadline from "../../shared/components/DashboardHeadline";
import InsightCard from "../../shared/components/InsightCard";
import MonthSelector from "../../shared/components/MonthSelector";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { metricDef } from "../../shared/insights/glossary";
import { officerBranchHeadline } from "../../shared/insights/headlines";
import { changeByProductInsight } from "../../shared/insights/rules";
import { emit } from "../../shared/telemetry/client";
import { formatCurrency } from "../../shared/utils/format";
import { spacing } from "../../theme/tokens";
import Banner from "../../ui/primitives/Banner";
import ChartCard from "../../ui/primitives/ChartCard";
import DataTable from "../../ui/primitives/DataTable";
import KpiTile from "../../ui/primitives/KpiTile";
import PageHeader from "../../ui/primitives/PageHeader";
import FiltersRow from "./FiltersRow";
import WatchlistTrend from "./WatchlistTrend";
import { useOfficerBranch } from "./api";
import {
	buildBorrowerRows,
	buildComboData,
	buildTabRows,
	buildWaterfallData,
	productLabel,
} from "./chartBuilders";

export { buildBorrowerRows, buildTabRows };

const LOADING_KEYS = ["a", "b", "c"];

const gridStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
	gap: spacing[6],
	marginBottom: spacing[6],
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

interface KpiTileSpec {
	label: string;
	value: string;
	infoTooltip?: string;
}

function tileFromDef(id: string, fallback: string, value: string): KpiTileSpec {
	const def = metricDef(id);
	return {
		label: def?.short ?? fallback,
		value,
		infoTooltip: def?.tooltip,
	};
}

function buildKpiTiles(d: OfficerBranchData | null): KpiTileSpec[] {
	if (!d) return [];
	return [
		tileFromDef("total_loans_balance", "Total Loans", formatCurrency(d.total_loans)),
		tileFromDef(
			"account_count",
			"Account Count",
			d.account_count.toLocaleString(),
		),
		tileFromDef(
			"avg_loan_balance",
			"Avg Loan Balance",
			formatCurrency(d.avg_loan_balance),
		),
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
				display: "grid",
				gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
				gap: spacing[4],
				marginBottom: spacing[6],
			}}
		>
			{loading
				? LOADING_KEYS.map((k) => <KpiTile key={k} label="" value="" loading />)
				: tiles.map((props) => <KpiTile key={props.label} {...props} />)}
		</div>
	);
}

export default function OfficerBranch() {
	const { asOfDate } = useDashboardContext();
	const [searchParams, setSearchParams] = useSearchParams();
	const tab = searchParams.get("tab");
	const branchId = searchParams.get("branch_id") ?? "";
	const officerId = searchParams.get("officer_id") ?? "";

	const { data, loading, isError } = useOfficerBranch({
		asOfDate,
		tab: tab ?? undefined,
		branchId: branchId ? Number(branchId) : undefined,
		officerId: officerId || undefined,
	});

	if (isError)
		return (
			<div>
				<PageHeader title="Officer / Branch Loans" eyebrow="Loan Portfolio" />
				<p role="alert">Failed to load Officer/Branch data.</p>
			</div>
		);

	return (
		<div>
			<PageHeader
				title="Officer / Branch Loans"
				eyebrow="Loan Portfolio"
				actions={<MonthSelector surface="officer-branch" />}
			/>
			{data && <DashboardHeadline headline={officerBranchHeadline(data)} />}
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
				<ChartCard
					title="Loan Mix by Product"
					subtitle="Share of loans by type (auto, mortgage, commercial, etc.)"
					loading={loading}
				>
					<Donut data={buildLoanMix(data)} loading={loading} />
				</ChartCard>
				<ChartCard
					title="Loan Movement by Product ($M)"
					subtitle="Month-to-date balance change broken out by product"
					loading={loading}
					footer={
						!loading && (
							<InsightCard
								{...changeByProductInsight(buildWaterfallData(data))}
							/>
						)
					}
				>
					<Waterfall data={buildWaterfallData(data)} loading={loading} />
				</ChartCard>
				<ChartCard
					title="Loans vs. Yield by Product"
					subtitle="Bars: balance ($M). Line: average interest rate (%)"
					loading={loading}
				>
					<Combo
						data={buildComboData(data)}
						barLabel="Balance ($M)"
						lineLabel="Avg rate (%)"
						loading={loading}
					/>
				</ChartCard>
			</div>

			{data?.tab_data && buildTabRows(data).length > 0 && (
				<ChartCard
					title={`Lifecycle: ${tab ?? "new"} loans`}
					subtitle="Recent activity by product, last 12 months"
					loading={loading}
				>
					<DataTable
						columns={["Period", "Product Type", "Count", "Amount"]}
						rows={buildTabRows(data)}
						loading={loading}
					/>
				</ChartCard>
			)}

			<WatchlistTrend data={data?.watchlist_trend ?? []} />

			<ChartCard
				title="Top Borrowers"
				subtitle="Largest individual loan relationships"
				loading={loading}
			>
				<DataTable
					columns={["Member", "Balance", "Share %"]}
					rows={buildBorrowerRows(data)}
					loading={loading}
				/>
			</ChartCard>
		</div>
	);
}
