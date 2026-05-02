import { useEffect, useMemo, useState } from "react";
import LineTrend from "../../../charts/LineTrend";
import type { AskResponse } from "../../../shared/api/api";
import { emit } from "../../../shared/telemetry/client";
import type { ChatResultType } from "../../../shared/telemetry/events";
import { colors, spacing, typography } from "../../../theme/tokens";
import DataTable from "../../../ui/primitives/DataTable";

interface Props {
	result: AskResponse;
}

const DATE_PATTERN = /^\d{4}-\d{2}(-\d{2})?$/;

function isNumber(v: unknown): v is number {
	return typeof v === "number" && Number.isFinite(v);
}

function pickDateColumn(
	rows: Record<string, unknown>[],
	columns: string[],
): string | null {
	if (rows.length < 2 || rows[0] === undefined) return null;
	const first = rows[0];
	for (const col of columns) {
		const v = first[col];
		if (typeof v === "string" && DATE_PATTERN.test(v)) return col;
	}
	return null;
}

function pickNumericColumn(
	rows: Record<string, unknown>[],
	columns: string[],
	exclude?: string,
): string | null {
	if (rows[0] === undefined) return null;
	for (const col of columns) {
		if (col === exclude) continue;
		if (isNumber(rows[0][col])) return col;
	}
	return null;
}

export function classifyResult(result: AskResponse): ChatResultType {
	if (result.clarification !== null) return "clarification";
	if (
		result.rows.length === 1 &&
		result.columns.length === 1 &&
		isNumber(result.rows[0]?.[result.columns[0] ?? ""])
	) {
		return "number";
	}
	if (
		pickDateColumn(result.rows, result.columns) !== null &&
		pickNumericColumn(
			result.rows,
			result.columns,
			pickDateColumn(result.rows, result.columns) ?? undefined,
		) !== null
	) {
		return "chart";
	}
	return "table";
}

const numberStyle: React.CSSProperties = {
	fontSize: typography.size["2xl"],
	fontWeight: typography.weight.bold,
	color: colors.slate[900],
	fontVariantNumeric: "tabular-nums",
	margin: `${spacing[2]} 0`,
};

const interpStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[500],
	margin: 0,
};

const clarStyle: React.CSSProperties = {
	padding: spacing[3],
	background: colors.indigo[50],
	border: `1px solid ${colors.indigo[100]}`,
	borderRadius: 6,
	color: colors.slate[800],
	fontSize: typography.size.sm,
};

const toggleStyle: React.CSSProperties = {
	background: "none",
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: 4,
	padding: `${spacing[1]} ${spacing[3]}`,
	fontSize: typography.size.xs,
	color: colors.slate[600],
	cursor: "pointer",
	marginBottom: spacing[2],
};

function NumberView({ result }: Props) {
	const col = result.columns[0] ?? "";
	const value = result.rows[0]?.[col];
	const display = isNumber(value)
		? value.toLocaleString()
		: String(value ?? "");
	return (
		<div>
			<p aria-label="Result value" style={numberStyle}>
				{display}
			</p>
			{result.explanation !== null && (
				<p style={interpStyle}>{result.explanation}</p>
			)}
		</div>
	);
}

function ChartView({ result }: Props) {
	const [asTable, setAsTable] = useState(false);
	const dateCol = pickDateColumn(result.rows, result.columns) ?? "";
	const numCol = pickNumericColumn(result.rows, result.columns, dateCol) ?? "";
	const data = useMemo(
		() =>
			result.rows.map((r) => ({
				period: String(r[dateCol] ?? ""),
				value: isNumber(r[numCol]) ? (r[numCol] as number) : 0,
			})),
		[result.rows, dateCol, numCol],
	);
	return (
		<div>
			<button
				type="button"
				aria-pressed={asTable}
				onClick={() => setAsTable((v) => !v)}
				style={toggleStyle}
			>
				{asTable ? "View as chart" : "View as table"}
			</button>
			{asTable ? (
				<DataTable columns={result.columns} rows={result.rows} />
			) : (
				<LineTrend data={data} seriesLabel={numCol} />
			)}
		</div>
	);
}

function TableView({ result }: Props) {
	if (result.rows.length === 0) {
		return (
			<p style={interpStyle}>{result.explanation ?? "No rows returned."}</p>
		);
	}
	return <DataTable columns={result.columns} rows={result.rows} />;
}

function ClarificationView({ result }: Props) {
	return (
		<p role="note" style={clarStyle}>
			{result.clarification}
		</p>
	);
}

export default function ResultRenderer({ result }: Props) {
	const kind = classifyResult(result);

	useEffect(() => {
		emit({
			type: "chat.result.rendered",
			query_id: result.request_id,
			row_count: result.rows.length,
			result_type: kind,
		});
	}, [result.request_id, result.rows.length, kind]);

	if (kind === "clarification") return <ClarificationView result={result} />;
	if (kind === "number") return <NumberView result={result} />;
	if (kind === "chart") return <ChartView result={result} />;
	return <TableView result={result} />;
}
