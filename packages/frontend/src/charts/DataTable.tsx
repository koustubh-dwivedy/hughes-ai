import { useState } from "react";
import { colors, typography } from "../theme/tokens";

const MAX_ROWS = 25;

interface SortState {
	col: string | null;
	dir: "asc" | "desc";
}

interface DataTableProps {
	columns: string[];
	rows: Record<string, unknown>[];
	loading?: boolean;
}

/**
 * @example
 * <DataTable
 *   columns={["officer", "balance", "count"]}
 *   rows={[
 *     { officer: "Smith", balance: 4.2, count: 12 },
 *     { officer: "Jones", balance: 3.8, count: 9 },
 *   ]}
 * />
 */
export default function DataTable({
	columns,
	rows,
	loading = false,
}: DataTableProps) {
	const [sort, setSort] = useState<SortState>({ col: null, dir: "asc" });

	if (loading) {
		return (
			<output
				aria-label="loading"
				style={{
					display: "flex",
					width: "100%",
					height: 120,
					backgroundColor: colors.slate[100],
					borderRadius: "0.5rem",
					alignItems: "center",
					justifyContent: "center",
					color: colors.slate[400],
					fontSize: typography.size.sm,
				}}
			>
				Loading…
			</output>
		);
	}

	if (rows.length === 0) {
		return (
			<p style={{ color: colors.slate[500], fontSize: typography.size.sm }}>
				No data
			</p>
		);
	}

	const sortCol = sort.col;
	const sorted = sortCol
		? [...rows].sort((a, b) => {
				const va = a[sortCol];
				const vb = b[sortCol];
				if (va === vb) return 0;
				const cmp =
					typeof va === "number" && typeof vb === "number"
						? (va as number) - (vb as number)
						: String(va).localeCompare(String(vb));
				return sort.dir === "asc" ? cmp : -cmp;
			})
		: rows;

	const visible = sorted.slice(0, MAX_ROWS);

	function handleSort(col: string) {
		setSort((prev) =>
			prev.col === col
				? { col, dir: prev.dir === "asc" ? "desc" : "asc" }
				: { col, dir: "asc" },
		);
	}

	return (
		<div style={{ overflowX: "auto" }}>
			<table
				style={{
					width: "100%",
					borderCollapse: "collapse",
					fontSize: typography.size.sm,
					color: colors.slate[700],
				}}
			>
				<thead>
					<tr style={{ borderBottom: `2px solid ${colors.slate[200]}` }}>
						{columns.map((col) => (
							<th
								key={col}
								style={{
									padding: "0.5rem 0.75rem",
									textAlign: "left",
									fontWeight: typography.weight.semibold,
									color: colors.slate[600],
									whiteSpace: "nowrap",
								}}
							>
								<button
									type="button"
									onClick={() => handleSort(col)}
									style={{
										background: "none",
										border: "none",
										cursor: "pointer",
										font: "inherit",
										color: "inherit",
										fontWeight: "inherit",
										padding: 0,
									}}
								>
									{col}
									{sort.col === col ? (sort.dir === "asc" ? " ▲" : " ▼") : ""}
								</button>
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{visible.map((row) => {
						const rowKey = columns.map((c) => String(row[c] ?? "")).join("|");
						return (
							<tr
								key={rowKey}
								style={{
									borderBottom: `1px solid ${colors.slate[100]}`,
								}}
							>
								{columns.map((col) => (
									<td key={col} style={{ padding: "0.5rem 0.75rem" }}>
										{String(row[col] ?? "")}
									</td>
								))}
							</tr>
						);
					})}
				</tbody>
			</table>
		</div>
	);
}
