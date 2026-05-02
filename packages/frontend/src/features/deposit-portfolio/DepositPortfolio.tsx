import Donut from "../../charts/Donut";
import Waterfall from "../../charts/Waterfall";
import type { DepositPortfolioData } from "../../shared/api/dashboardApi";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { emit } from "../../shared/telemetry/client";
import { formatCurrency } from "../../shared/utils/format";
import { spacing } from "../../theme/tokens";
import ChartCard from "../../ui/primitives/ChartCard";
import DataTable from "../../ui/primitives/DataTable";
import DateBadge from "../../ui/primitives/DateBadge";
import KpiTile from "../../ui/primitives/KpiTile";
import PageHeader from "../../ui/primitives/PageHeader";
import { useDepositPortfolio } from "./api";

const TOP_SLICES = 3;
const LOADING_KEYS = ["a", "b", "c", "d", "e"];

const tilesRowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
	gap: spacing[4],
	marginBottom: spacing[6],
};

const gridStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
	gap: spacing[6],
	marginBottom: spacing[6],
};

function onTile(kpi_id: string, value: number) {
	emit({ type: "kpi.tile.clicked", kpi_id, value });
}

function topWithOther(data: DepositPortfolioData) {
	const sorted = [...data.deposit_mix].sort((a, b) => b.balance - a.balance);
	const top = sorted.slice(0, TOP_SLICES);
	const others = sorted.slice(TOP_SLICES);
	const otherTotal = others.reduce((s, d) => s + d.balance, 0);
	const slices = top.map((d) => ({ label: d.product, value: d.balance }));
	if (otherTotal > 0) slices.push({ label: "Other", value: otherTotal });
	return slices;
}

function buildKpiTiles(d: DepositPortfolioData) {
	const mtdDelta =
		d.mtd_change >= 0
			? `↑ ${formatCurrency(d.mtd_change)}`
			: `↓ ${formatCurrency(Math.abs(d.mtd_change))}`;
	return [
		{
			id: "total_deposits",
			label: "Total Deposits",
			value: formatCurrency(d.total_deposits),
			delta: mtdDelta,
			deltaPositive: d.mtd_change >= 0,
			onClick: () => onTile("total_deposits", d.total_deposits),
		},
		{
			id: "mtd_change",
			label: "MTD Change",
			value: formatCurrency(d.mtd_change),
			deltaPositive: d.mtd_change >= 0,
			onClick: () => onTile("mtd_change", d.mtd_change),
		},
		{
			id: "ytd_change",
			label: "YTD Change",
			value: formatCurrency(d.ytd_change),
			deltaPositive: d.ytd_change >= 0,
			onClick: () => onTile("ytd_change", d.ytd_change),
		},
		{
			id: "account_count",
			label: "Account Count",
			value: d.account_count.toLocaleString(),
			onClick: () => onTile("account_count", d.account_count),
		},
		{
			id: "avg_balance",
			label: "Avg Balance",
			value: formatCurrency(d.avg_balance_per_customer),
			onClick: () =>
				onTile("avg_balance_per_customer", d.avg_balance_per_customer),
		},
	];
}

export default function DepositPortfolio() {
	const { asOfDate } = useDashboardContext();
	const { data, loading, isError } = useDepositPortfolio({ asOfDate });

	if (isError)
		return (
			<div>
				<PageHeader title="Deposit Portfolio" eyebrow="Deposits" />
				<p role="alert">Failed to load deposit portfolio.</p>
			</div>
		);

	const kpiTiles = data ? buildKpiTiles(data) : [];
	const mixSlices = data ? topWithOther(data) : [];
	const branchRows = data
		? data.deposits_by_branch.map((d) => ({
				Branch: d.branch_name,
				Balance: formatCurrency(d.balance),
			}))
		: [];
	const waterfallData = data
		? data.change_by_product.map((d) => ({
				label: d.product,
				value: d.delta / 1_000_000,
			}))
		: [];
	const depositorRows = data
		? data.top_25_deposits.map((d) => ({
				Member: d.member_name,
				Balance: formatCurrency(d.balance),
				"Share %": `${d.share_pct.toFixed(1)}%`,
			}))
		: [];

	const centerLabel = data ? formatCurrency(data.total_deposits) : undefined;
	const opened = data?.new_vs_closed_accounts.opened;
	const closed = data?.new_vs_closed_accounts.closed;

	return (
		<div>
			<PageHeader
				title="Deposit Portfolio"
				eyebrow="Deposits"
				dateBadge={asOfDate ? <DateBadge asOfDate={asOfDate} /> : undefined}
			/>

			<div style={tilesRowStyle}>
				{loading
					? LOADING_KEYS.slice(0, 5).map((k) => (
							<KpiTile key={k} label="" value="" loading />
						))
					: kpiTiles.map(({ id: _id, ...props }) => (
							<KpiTile key={props.label} {...props} />
						))}
			</div>

			<div style={tilesRowStyle}>
				{!loading && opened && closed && (
					<>
						<KpiTile
							label="New Accounts"
							value={opened.count.toLocaleString()}
							delta={formatCurrency(opened.amount)}
							deltaPositive
							onClick={() => onTile("new_accounts", opened.count)}
						/>
						<KpiTile
							label="Closed Accounts"
							value={closed.count.toLocaleString()}
							delta={formatCurrency(closed.amount)}
							deltaPositive={false}
							onClick={() => onTile("closed_accounts", closed.count)}
						/>
					</>
				)}
			</div>

			<div style={gridStyle}>
				<ChartCard title="Deposit Mix" loading={loading}>
					<Donut data={mixSlices} centerLabel={centerLabel} loading={loading} />
				</ChartCard>
				<ChartCard title="Change by Product ($M)" loading={loading}>
					<Waterfall data={waterfallData} loading={loading} />
				</ChartCard>
			</div>

			<ChartCard title="Deposits by Branch" loading={loading}>
				<DataTable
					columns={["Branch", "Balance"]}
					rows={branchRows}
					loading={loading}
				/>
			</ChartCard>

			<ChartCard title="Top Depositors" loading={loading}>
				<DataTable
					columns={["Member", "Balance", "Share %"]}
					rows={depositorRows}
					loading={loading}
				/>
			</ChartCard>
		</div>
	);
}
