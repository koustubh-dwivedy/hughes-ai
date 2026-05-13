import Combo from "../../charts/Combo";
import Donut from "../../charts/Donut";
import KpiTile from "../../charts/KpiTile";
import StackedBar from "../../charts/StackedBar";
import Waterfall from "../../charts/Waterfall";
import DashboardShell from "../../layout/DashboardShell";
import { getDepositPortfolio } from "../../shared/api/api";
import type { DepositPortfolioData } from "../../shared/api/dashboardApi";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { useDashboard } from "../../shared/hooks/useDashboard";
import { spacing } from "../../theme/tokens";
import DataTable from "../../ui/primitives/DataTable";

function fmt(n: number): string {
	return `$${(n / 1_000_000).toFixed(1)}M`;
}

function buildNvcData(
	data: DepositPortfolioData | null,
): { period: string; bar: number; line: number }[] {
	if (!data) return [];
	const { opened, closed } = data.new_vs_closed_accounts;
	return [
		{ period: "Opened", bar: opened.count, line: opened.amount / 1_000_000 },
		{ period: "Closed", bar: closed.count, line: closed.amount / 1_000_000 },
	];
}

export default function DepositPortfolio() {
	const { asOfDate } = useDashboardContext();
	const { data, loading, error } = useDashboard(getDepositPortfolio, {
		asOfDate,
	});

	const mixSlices =
		data?.deposit_mix.map((d) => ({ label: d.product, value: d.balance })) ??
		[];
	const branchData =
		data?.deposits_by_branch.map((d) => ({
			period: d.branch_name,
			balance: d.balance,
		})) ?? [];
	const waterfallData =
		data?.change_by_product.map((d) => ({
			label: d.product,
			value: d.delta,
		})) ?? [];
	const nvcData = buildNvcData(data);
	const tableColumns = ["Member", "Balance", "Share %"];
	const tableRows =
		data?.top_25_deposits.map((d) => ({
			Member: d.member_name,
			Balance: fmt(d.balance),
			"Share %": `${d.share_pct.toFixed(1)}%`,
		})) ?? [];

	return (
		<DashboardShell
			title="Deposit Portfolio"
			loading={loading}
			error={error}
			empty={!loading && !error && !data}
		>
			<div
				style={{
					display: "flex",
					gap: spacing[4],
					flexWrap: "wrap",
					marginBottom: spacing[6],
				}}
			>
				<KpiTile
					label="Total Deposits"
					value={fmt(data?.total_deposits ?? 0)}
				/>
				<KpiTile
					label="MTD Change"
					value={fmt(data?.mtd_change ?? 0)}
					delta={data?.mtd_change}
				/>
				<KpiTile
					label="YTD Change"
					value={fmt(data?.ytd_change ?? 0)}
					delta={data?.ytd_change}
				/>
				<KpiTile
					label="Account Count"
					value={(data?.account_count ?? 0).toLocaleString()}
				/>
				<KpiTile
					label="Avg Balance"
					value={fmt(data?.avg_balance_per_customer ?? 0)}
				/>
			</div>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: spacing[6],
					marginBottom: spacing[6],
				}}
			>
				<Donut data={mixSlices} title="Deposit Mix" loading={loading} />
				<StackedBar
					data={branchData}
					series={[{ key: "balance" }]}
					title="Deposits by Branch"
					loading={loading}
					xAxisType="categorical"
				/>
				<Waterfall
					data={waterfallData}
					title="Change by Product ($M)"
					loading={loading}
				/>
				<Combo
					data={nvcData}
					barLabel="Count"
					lineLabel="Amount ($M)"
					title="New vs Closed Accounts"
					loading={loading}
				/>
			</div>

			<DataTable columns={tableColumns} rows={tableRows} loading={loading} />
		</DashboardShell>
	);
}
