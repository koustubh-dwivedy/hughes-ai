import {
	KBarAnimator,
	KBarPortal,
	KBarPositioner,
	KBarResults,
	KBarSearch,
	useMatches,
} from "kbar";
import type { ActionImpl } from "kbar";
import { colors, radii, spacing, typography } from "../../theme/tokens";

const overlayStyle: React.CSSProperties = {
	background: "rgba(0, 0, 0, 0.45)",
	zIndex: 9999,
};

const animatorStyle: React.CSSProperties = {
	maxWidth: 600,
	width: "100%",
	background: colors.white,
	borderRadius: radii.lg,
	boxShadow: "0 16px 48px rgba(0,0,0,0.18), 0 4px 12px rgba(0,0,0,0.12)",
	overflow: "hidden",
};

const searchStyle: React.CSSProperties = {
	padding: `${spacing[4]} ${spacing[4]}`,
	fontSize: typography.size.base,
	fontFamily: typography.fontFamily,
	width: "100%",
	boxSizing: "border-box",
	outline: "none",
	border: "none",
	borderBottom: `1px solid ${colors.slate[200]}`,
	color: colors.slate[900],
	background: "transparent",
};

const sectionStyle: React.CSSProperties = {
	padding: `${spacing[2]} ${spacing[4]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[400],
	letterSpacing: "0.08em",
	textTransform: "uppercase",
	background: colors.slate[50],
};

function resultItemStyle(active: boolean): React.CSSProperties {
	return {
		display: "flex",
		alignItems: "center",
		padding: `${spacing[3]} ${spacing[4]}`,
		fontSize: typography.size.sm,
		fontFamily: typography.fontFamily,
		color: active ? colors.indigo[700] : colors.slate[800],
		background: active ? colors.indigo[50] : "transparent",
		cursor: "pointer",
		gap: spacing[3],
	};
}

function ResultItem({
	action,
	active,
}: { action: ActionImpl; active: boolean }) {
	return (
		<div style={resultItemStyle(active)}>
			<span style={{ flex: 1 }}>{action.name}</span>
			{action.subtitle && (
				<span
					style={{
						fontSize: typography.size.xs,
						color: colors.slate[400],
					}}
				>
					{action.subtitle}
				</span>
			)}
		</div>
	);
}

function RenderResults() {
	const { results } = useMatches();
	return (
		<KBarResults
			items={results}
			onRender={({ item, active }) =>
				typeof item === "string" ? (
					<div style={sectionStyle}>{item}</div>
				) : (
					<ResultItem action={item} active={active} />
				)
			}
		/>
	);
}

export default function CommandPalette() {
	return (
		<KBarPortal>
			<KBarPositioner style={overlayStyle}>
				<KBarAnimator style={animatorStyle}>
					<KBarSearch
						style={searchStyle}
						placeholder="Search dashboards and actions…"
					/>
					<RenderResults />
				</KBarAnimator>
			</KBarPositioner>
		</KBarPortal>
	);
}
