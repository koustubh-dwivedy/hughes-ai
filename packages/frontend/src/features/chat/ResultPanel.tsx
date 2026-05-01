import { Bar, BarChart, Tooltip, XAxis, YAxis } from "recharts";
import type { AskResponse } from "../../shared/api/api";

interface Props {
	result: AskResponse;
}

function isNumber(v: unknown): v is number {
	return typeof v === "number";
}

function DataTable({
	rows,
	columns,
}: {
	rows: Record<string, unknown>[];
	columns: string[];
}) {
	return (
		<table>
			<thead>
				<tr>
					{columns.map((c) => (
						<th key={c}>{c}</th>
					))}
				</tr>
			</thead>
			<tbody>
				{rows.map((row, i) => (
					// biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
					<tr key={i}>
						{columns.map((c) => (
							<td key={c}>{String(row[c] ?? "")}</td>
						))}
					</tr>
				))}
			</tbody>
		</table>
	);
}

function RowsDisplay({
	rows,
	columns,
}: {
	rows: Record<string, unknown>[];
	columns: string[];
}) {
	if (rows.length === 0) return null;
	const numCol = columns.find((c) => isNumber(rows[0][c]));
	const catCol = columns.find((c) => !isNumber(rows[0][c]));
	if (numCol !== undefined && catCol !== undefined && rows.length <= 20) {
		return (
			<BarChart width={600} height={280} data={rows}>
				<XAxis dataKey={catCol} />
				<YAxis />
				<Tooltip />
				<Bar dataKey={numCol} />
			</BarChart>
		);
	}
	return <DataTable rows={rows} columns={columns} />;
}

export default function ResultPanel({ result }: Props) {
	if (result.clarification !== null) {
		return <p>{result.clarification}</p>;
	}
	return (
		<section style={{ marginTop: "1.5rem" }}>
			{result.explanation !== null && <p>{result.explanation}</p>}
			<RowsDisplay rows={result.rows} columns={result.columns} />
			{result.caveats.length > 0 && (
				<details>
					<summary>Caveats ({result.caveats.length})</summary>
					<ul>
						{result.caveats.map((c) => (
							<li key={c}>{c}</li>
						))}
					</ul>
				</details>
			)}
			{result.assumptions.length > 0 && (
				<details>
					<summary>Assumptions</summary>
					<ul>
						{result.assumptions.map((a) => (
							<li key={a}>{a}</li>
						))}
					</ul>
				</details>
			)}
			{result.tables_used.length > 0 && (
				<details>
					<summary>Lineage</summary>
					<ul>
						{result.tables_used.map((t) => (
							<li key={t}>{t}</li>
						))}
					</ul>
				</details>
			)}
			{result.sql !== null && (
				<details>
					<summary>SQL</summary>
					<pre>
						<code>{result.sql}</code>
					</pre>
				</details>
			)}
		</section>
	);
}
