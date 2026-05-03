import { colors, radii, spacing, typography } from "../../theme/tokens";
import type { DashboardLink, LayerName } from "./types";
import { LAYER_ORDER } from "./types";

export interface FilterState {
	enabledLayers: Set<LayerName>;
	dashboardId: string | null;
}

interface Props {
	state: FilterState;
	dashboards: DashboardLink[];
	onToggleLayer: (layer: LayerName) => void;
	onSelectDashboard: (id: string | null) => void;
}

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	flexWrap: "wrap",
	gap: spacing[6],
	rowGap: spacing[2],
	padding: `${spacing[2]} ${spacing[4]}`,
	borderBottom: `1px solid ${colors.slate[200]}`,
	background: colors.slate[50],
	alignItems: "center",
	flexShrink: 0,
};

const groupStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	gap: spacing[2],
};

const labelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.06em",
};

// Segmented-control container: chips share a common border so the group reads
// as one unit rather than a row of loose pills.
const segmentStyle: React.CSSProperties = {
	display: "inline-flex",
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.md,
	background: colors.white,
	overflow: "hidden",
};

function segmentItemStyle(
	active: boolean,
	first: boolean,
	last: boolean,
): React.CSSProperties {
	return {
		fontSize: typography.size.xs,
		padding: `4px ${spacing[3]}`,
		border: "none",
		borderLeft: first ? "none" : `1px solid ${colors.slate[200]}`,
		borderTopLeftRadius: first ? radii.md : 0,
		borderBottomLeftRadius: first ? radii.md : 0,
		borderTopRightRadius: last ? radii.md : 0,
		borderBottomRightRadius: last ? radii.md : 0,
		background: active ? colors.indigo[700] : colors.white,
		color: active ? colors.white : colors.slate[700],
		fontWeight: active ? typography.weight.medium : typography.weight.normal,
		fontFamily: typography.fontFamily,
		cursor: "pointer",
		transition: "background 80ms ease, color 80ms ease",
	};
}

interface SegmentOption<T> {
	key: T;
	label: string;
	active: boolean;
	onClick: () => void;
}

function Segment<T extends string>({
	options,
}: { options: SegmentOption<T>[] }) {
	return (
		<fieldset style={{ ...segmentStyle, padding: 0, margin: 0 }}>
			{options.map((opt, i) => (
				<button
					key={opt.key}
					type="button"
					aria-pressed={opt.active}
					onClick={opt.onClick}
					style={segmentItemStyle(
						opt.active,
						i === 0,
						i === options.length - 1,
					)}
				>
					{opt.label}
				</button>
			))}
		</fieldset>
	);
}

export default function FilterBar({
	state,
	dashboards,
	onToggleLayer,
	onSelectDashboard,
}: Props) {
	const layerOptions: SegmentOption<LayerName>[] = LAYER_ORDER.map((layer) => ({
		key: layer,
		label: layer,
		active: state.enabledLayers.has(layer),
		onClick: () => onToggleLayer(layer),
	}));

	const dashboardOptions: SegmentOption<string>[] = [
		{
			key: "__all__",
			label: "All",
			active: state.dashboardId === null,
			onClick: () => onSelectDashboard(null),
		},
		...dashboards.map((d) => ({
			key: d.id,
			label: d.name,
			active: state.dashboardId === d.id,
			onClick: () =>
				onSelectDashboard(state.dashboardId === d.id ? null : d.id),
		})),
	];

	return (
		<div style={wrapperStyle} role="toolbar" aria-label="Data model filters">
			<div style={groupStyle}>
				<span style={labelStyle}>Layers</span>
				<Segment options={layerOptions} />
			</div>
			<div style={groupStyle}>
				<span style={labelStyle}>Dashboard</span>
				<Segment options={dashboardOptions} />
			</div>
		</div>
	);
}
