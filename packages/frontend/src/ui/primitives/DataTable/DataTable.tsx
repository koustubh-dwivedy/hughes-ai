import { ActionIcon, Group, Table } from "@mantine/core";
import { useState } from "react";
import type { DataTableProps, Density } from "./types";

const MAX_ROWS = 25;

interface SortState {
	col: string | null;
	dir: "asc" | "desc";
}

function SortChevron({ dir }: { dir: "asc" | "desc" | null }) {
	if (dir === null) {
		return (
			<svg
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				strokeWidth={2}
				style={{ opacity: 0.3 }}
				aria-hidden
			>
				<title>Sortable</title>
				<path d="M8 9l4-4 4 4M16 15l-4 4-4-4" />
			</svg>
		);
	}
	return dir === "asc" ? (
		<svg
			width="12"
			height="12"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth={2}
			aria-hidden
		>
			<title>Ascending</title>
			<path d="M18 15l-6-6-6 6" />
		</svg>
	) : (
		<svg
			width="12"
			height="12"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth={2}
			aria-hidden
		>
			<title>Descending</title>
			<path d="M6 9l6 6 6-6" />
		</svg>
	);
}

function isNumeric(val: unknown): boolean {
	return typeof val === "number";
}

export default function DataTable({
	columns,
	rows,
	loading = false,
	density: initialDensity = "default",
}: DataTableProps) {
	const [sort, setSort] = useState<SortState>({ col: null, dir: "asc" });
	const [density, setDensity] = useState<Density>(initialDensity);

	if (loading) {
		return (
			<output
				aria-label="loading"
				style={{
					display: "block",
					padding: "2rem",
					textAlign: "center",
					color: "var(--mantine-color-gray-5)",
				}}
			>
				Loading…
			</output>
		);
	}

	if (rows.length === 0) {
		return (
			<p style={{ color: "var(--mantine-color-gray-6)", fontSize: "0.875rem" }}>
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

	const verticalSpacing = density === "compact" ? "xs" : "sm";

	return (
		<div>
			<Group justify="flex-end" mb="xs">
				<ActionIcon
					size="sm"
					variant={density === "compact" ? "filled" : "subtle"}
					aria-label="density toggle"
					onClick={() =>
						setDensity((d) => (d === "compact" ? "default" : "compact"))
					}
					aria-pressed={density === "compact"}
				>
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth={2}
						aria-hidden
					>
						<title>Toggle density</title>
						<path d="M3 6h18M3 12h18M3 18h18" />
					</svg>
				</ActionIcon>
			</Group>

			<Table
				stickyHeader
				striped
				highlightOnHover
				withTableBorder
				withColumnBorders={false}
				verticalSpacing={verticalSpacing}
				style={{ fontSize: "0.875rem" }}
			>
				<Table.Thead>
					<Table.Tr>
						{columns.map((col) => (
							<Table.Th key={col} style={{ whiteSpace: "nowrap" }}>
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
										display: "inline-flex",
										alignItems: "center",
										gap: "0.25rem",
									}}
								>
									{col}
									<SortChevron dir={sort.col === col ? sort.dir : null} />
								</button>
							</Table.Th>
						))}
					</Table.Tr>
				</Table.Thead>
				<Table.Tbody>
					{visible.map((row) => {
						const rowKey = columns.map((c) => String(row[c] ?? "")).join("|");
						return (
							<Table.Tr key={rowKey}>
								{columns.map((col) => {
									const val = row[col];
									const numeric = isNumeric(val);
									return (
										<Table.Td
											key={col}
											style={
												numeric
													? {
															fontVariantNumeric: "tabular-nums",
															textAlign: "right",
														}
													: undefined
											}
										>
											{String(val ?? "")}
										</Table.Td>
									);
								})}
							</Table.Tr>
						);
					})}
				</Table.Tbody>
			</Table>
		</div>
	);
}
