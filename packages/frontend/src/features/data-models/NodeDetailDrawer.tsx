import { Drawer } from "@mantine/core";
import { Link } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import SqlBlock from "../../ui/primitives/SqlBlock";
import { useGetDataModelNodeQuery } from "./api";
import { LAYER_STYLES } from "./layerStyles";
import type { ColumnInfo, NodeDetail } from "./types";

interface Props {
	nodeId: string | null;
	onClose: () => void;
	onJumpTo: (id: string) => void;
}

const sectionLabelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[600],
	textTransform: "uppercase",
	letterSpacing: "0.04em",
	margin: `${spacing[3]} 0 ${spacing[1]}`,
};

const metaStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	color: colors.slate[600],
	fontFamily: "ui-monospace, SFMono-Regular, monospace",
};

const chipStyle = (active = false): React.CSSProperties => ({
	display: "inline-block",
	fontSize: typography.size.xs,
	padding: `2px ${spacing[2]}`,
	border: `1px solid ${active ? colors.indigo[700] : colors.slate[300]}`,
	background: active ? colors.indigo[50] : colors.white,
	color: colors.slate[700],
	borderRadius: radii.sm,
	margin: "2px 4px 2px 0",
	cursor: "pointer",
	textDecoration: "none",
	fontFamily: typography.fontFamily,
});

function ColumnsTable({ columns }: { columns: ColumnInfo[] }) {
	if (columns.length === 0) {
		return <p style={metaStyle}>No columns documented.</p>;
	}
	return (
		<table
			style={{
				width: "100%",
				borderCollapse: "collapse",
				fontSize: typography.size.xs,
			}}
		>
			<thead>
				<tr>
					{["Name", "Type", "Description"].map((h) => (
						<th
							key={h}
							style={{
								textAlign: "left",
								padding: `${spacing[1]} ${spacing[2]}`,
								borderBottom: `1px solid ${colors.slate[200]}`,
								color: colors.slate[600],
								fontWeight: typography.weight.semibold,
							}}
						>
							{h}
						</th>
					))}
				</tr>
			</thead>
			<tbody>
				{columns.map((c) => (
					<tr key={c.name}>
						<td
							style={{
								padding: `${spacing[1]} ${spacing[2]}`,
								fontFamily: "ui-monospace, monospace",
							}}
						>
							{c.name}
						</td>
						<td
							style={{
								padding: `${spacing[1]} ${spacing[2]}`,
								color: colors.slate[600],
							}}
						>
							{c.type ?? "—"}
						</td>
						<td
							style={{
								padding: `${spacing[1]} ${spacing[2]}`,
								color: colors.slate[700],
							}}
						>
							{c.description ?? ""}
						</td>
					</tr>
				))}
			</tbody>
		</table>
	);
}

function DrawerBody({
	detail,
	onJumpTo,
}: { detail: NodeDetail; onJumpTo: (id: string) => void }) {
	const accent = LAYER_STYLES[detail.layer].accent;
	return (
		<div>
			<div style={{ display: "flex", alignItems: "center", gap: spacing[2] }}>
				<span
					style={{
						display: "inline-block",
						background: accent,
						color: colors.white,
						padding: `2px ${spacing[2]}`,
						borderRadius: radii.sm,
						fontSize: typography.size.xs,
						fontWeight: typography.weight.medium,
					}}
				>
					{detail.layer}
				</span>
				{detail.materialization !== null && (
					<span style={metaStyle}>materialized: {detail.materialization}</span>
				)}
				{detail.nl_query_count_30d > 0 && (
					<span style={{ ...metaStyle, marginLeft: "auto" }}>
						Asked in {detail.nl_query_count_30d} NL quer
						{detail.nl_query_count_30d === 1 ? "y" : "ies"} (30d)
					</span>
				)}
			</div>

			{detail.description !== null && (
				<p
					style={{
						marginTop: spacing[3],
						fontSize: typography.size.sm,
						color: colors.slate[800],
					}}
				>
					{detail.description}
				</p>
			)}

			{detail.file_path !== null && (
				<p style={{ ...metaStyle, marginTop: spacing[2] }}>
					{detail.file_path}
				</p>
			)}

			{detail.dashboards.length > 0 && (
				<>
					<p style={sectionLabelStyle}>Powers dashboards</p>
					<div>
						{detail.dashboards.map((d) => (
							<Link key={d.id} to={d.route} style={chipStyle(true)}>
								{d.name}
							</Link>
						))}
					</div>
				</>
			)}

			{detail.parents.length > 0 && (
				<>
					<p style={sectionLabelStyle}>Upstream ({detail.parents.length})</p>
					<div>
						{detail.parents.map((p) => (
							<button
								key={p}
								type="button"
								onClick={() => onJumpTo(p)}
								style={chipStyle(false)}
							>
								{p.split(".").pop() ?? p}
							</button>
						))}
					</div>
				</>
			)}

			{detail.children.length > 0 && (
				<>
					<p style={sectionLabelStyle}>Downstream ({detail.children.length})</p>
					<div>
						{detail.children.map((c) => (
							<button
								key={c}
								type="button"
								onClick={() => onJumpTo(c)}
								style={chipStyle(false)}
							>
								{c.split(".").pop() ?? c}
							</button>
						))}
					</div>
				</>
			)}

			{detail.columns.length > 0 && (
				<>
					<p style={sectionLabelStyle}>Columns ({detail.columns.length})</p>
					<ColumnsTable columns={detail.columns} />
				</>
			)}

			{detail.sql !== null && (
				<>
					<p style={sectionLabelStyle}>SQL</p>
					<SqlBlock sql={detail.sql} />
				</>
			)}
		</div>
	);
}

export default function NodeDetailDrawer({ nodeId, onClose, onJumpTo }: Props) {
	const skip = nodeId === null;
	const { data, isFetching, isError } = useGetDataModelNodeQuery(nodeId ?? "", {
		skip,
	});

	const title = data?.name ?? (isFetching ? "Loading…" : "");

	return (
		<Drawer
			opened={!skip}
			onClose={onClose}
			position="right"
			size="lg"
			title={title}
			withCloseButton
			padding="lg"
			aria-label="Data model node detail"
		>
			{isError && (
				<p style={{ color: colors.slate[700] }}>Failed to load node detail.</p>
			)}
			{!isError && data !== undefined && (
				<DrawerBody detail={data} onJumpTo={onJumpTo} />
			)}
		</Drawer>
	);
}
