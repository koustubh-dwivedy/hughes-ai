import type { Meta, StoryObj } from "@storybook/react";
import DataTable from "./DataTable";

const meta: Meta<typeof DataTable> = {
	component: DataTable,
	title: "Primitives/DataTable",
};
export default meta;

type Story = StoryObj<typeof DataTable>;

const loanRows = Array.from({ length: 25 }, (_, i) => ({
	"Loan ID": `L${String(i + 1).padStart(4, "0")}`,
	Officer: ["Smith", "Jones", "Taylor", "Brown", "Davis"][i % 5],
	Branch: ["Main", "East", "West", "North", "South"][i % 5],
	Balance: Math.round(10000 + i * 3750),
	Rate: +(4.5 + i * 0.1).toFixed(2),
	Status: i % 7 === 0 ? "Delinquent" : "Current",
}));

export const AuditReference: Story = {
	render: () => (
		<DataTable
			columns={["Loan ID", "Officer", "Branch", "Balance", "Rate", "Status"]}
			rows={loanRows}
		/>
	),
};

export const Compact: Story = {
	render: () => (
		<DataTable
			columns={["Loan ID", "Officer", "Branch", "Balance", "Rate", "Status"]}
			rows={loanRows}
			density="compact"
		/>
	),
};

export const Loading: Story = {
	render: () => <DataTable columns={["name", "score"]} rows={[]} loading />,
};

export const Empty: Story = {
	render: () => <DataTable columns={["name", "score"]} rows={[]} />,
};
