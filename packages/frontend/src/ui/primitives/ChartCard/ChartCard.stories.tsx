import type { Meta, StoryObj } from "@storybook/react";
import Donut from "../../../charts/Donut";
import LineTrend from "../../../charts/LineTrend";
import StackedBar from "../../../charts/StackedBar";
import ChartCard from "./ChartCard";

const meta: Meta<typeof ChartCard> = {
	component: ChartCard,
	title: "Primitives/ChartCard",
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof ChartCard>;

const donutData = [
	{ label: "Current", value: 820 },
	{ label: "30-59 DPD", value: 43 },
	{ label: "60-89 DPD", value: 12 },
	{ label: "90+ DPD", value: 8 },
];

const lineData = [
	{ period: "2025-04", value: 2.1 },
	{ period: "2025-05", value: 2.3 },
	{ period: "2025-06", value: 2.0 },
	{ period: "2025-07", value: 2.4 },
	{ period: "2025-08", value: 2.2 },
	{ period: "2025-09", value: 2.6 },
	{ period: "2025-10", value: 2.5 },
	{ period: "2025-11", value: 2.8 },
	{ period: "2025-12", value: 2.7 },
	{ period: "2026-01", value: 3.0 },
	{ period: "2026-02", value: 3.1 },
	{ period: "2026-03", value: 2.9 },
	{ period: "2026-04", value: 3.2 },
];

const stackData = [
	{ period: "Jan '26", auto: 12, mortgage: 28, personal: 8 },
	{ period: "Feb '26", auto: 13, mortgage: 27, personal: 9 },
	{ period: "Mar '26", auto: 11, mortgage: 29, personal: 10 },
	{ period: "Apr '26", auto: 14, mortgage: 26, personal: 11 },
];

const stackSeries = [{ key: "auto" }, { key: "mortgage" }, { key: "personal" }];

export const WithDonut: Story = {
	render: () => (
		<ChartCard title="Loan Status Mix" subtitle="As of April 2026">
			<Donut data={donutData} />
		</ChartCard>
	),
};

export const WithLineTrend: Story = {
	render: () => (
		<ChartCard title="Delinquency Rate Trend" subtitle="13-month rolling">
			<LineTrend data={lineData} seriesLabel="DQ Rate (%)" />
		</ChartCard>
	),
};

export const WithStackedBar: Story = {
	render: () => (
		<ChartCard title="Product Mix by Month" subtitle="Balance share (%)">
			<StackedBar data={stackData} series={stackSeries} />
		</ChartCard>
	),
};

export const WithActions: Story = {
	render: () => (
		<ChartCard
			title="Portfolio Balance"
			subtitle="By product type"
			actions={
				<button
					type="button"
					style={{ fontSize: "0.75rem", padding: "4px 8px" }}
				>
					Export
				</button>
			}
		>
			<Donut data={donutData} />
		</ChartCard>
	),
};

export const WithFooter: Story = {
	render: () => (
		<ChartCard
			title="Loan Status Mix"
			subtitle="As of April 2026"
			footer="Source: Origence LOS — synthetic data only"
		>
			<Donut data={donutData} />
		</ChartCard>
	),
};

export const Loading: Story = {
	render: () => <ChartCard title="Loading Chart" loading />,
};
