import { Handle, Position } from "reactflow";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import { LAYER_STYLES } from "./layerStyles";
import type { GraphNode } from "./types";

interface NodeProps {
	data: GraphNode & { dimmed?: boolean; highlighted?: boolean };
	selected?: boolean;
}

export default function LayerNode({ data, selected }: NodeProps) {
	const style = LAYER_STYLES[data.layer];
	const dim = data.dimmed === true;
	const hi = data.highlighted === true;

	const wrapper: React.CSSProperties = {
		width: 200,
		minHeight: 64,
		padding: `${spacing[2]} ${spacing[3]}`,
		background: style.background,
		border: `${selected || hi ? "2px" : "1px"} solid ${
			selected ? colors.indigo[700] : hi ? style.accent : style.border
		}`,
		borderRadius: radii.md,
		boxShadow: hi ? `0 0 0 3px ${colors.indigo[100]}` : "none",
		opacity: dim ? 0.3 : 1,
		fontFamily: typography.fontFamily,
		display: "flex",
		flexDirection: "column",
		gap: 4,
		transition: "opacity 120ms ease, box-shadow 120ms ease",
	};

	const nameStyle: React.CSSProperties = {
		fontSize: typography.size.sm,
		fontWeight: typography.weight.semibold,
		color: colors.slate[800],
		overflow: "hidden",
		textOverflow: "ellipsis",
		whiteSpace: "nowrap",
	};

	const metaStyle: React.CSSProperties = {
		fontSize: typography.size.xs,
		color: style.accent,
		display: "flex",
		justifyContent: "space-between",
		alignItems: "center",
		gap: spacing[2],
	};

	const badgeStyle: React.CSSProperties = {
		fontSize: typography.size.xs,
		fontWeight: typography.weight.medium,
		color: colors.indigo[700],
		background: colors.indigo[100],
		padding: "1px 6px",
		borderRadius: radii.sm,
	};

	return (
		<div style={wrapper}>
			<Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
			<div style={nameStyle}>{data.name}</div>
			<div style={metaStyle}>
				<span>{data.layer}</span>
				{data.nl_query_count_30d > 0 && (
					<span style={badgeStyle} title="Asked in NL queries (last 30d)">
						{data.nl_query_count_30d} ask
						{data.nl_query_count_30d === 1 ? "" : "s"}
					</span>
				)}
			</div>
			<Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
		</div>
	);
}
