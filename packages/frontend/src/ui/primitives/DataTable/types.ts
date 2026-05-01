export type Density = "compact" | "default";

export interface DataTableProps {
	columns: string[];
	rows: Record<string, unknown>[];
	loading?: boolean;
	density?: Density;
}
