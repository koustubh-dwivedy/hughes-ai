import { useKBar } from "kbar";
import { Search } from "lucide-react";
import { TENANT } from "../../shared/branding";
import { colors, radii, spacing, typography } from "../../theme/tokens";

const stripStyle: React.CSSProperties = {
	height: 64,
	minHeight: 64,
	display: "flex",
	alignItems: "center",
	justifyContent: "space-between",
	padding: `0 ${spacing[6]}`,
	backgroundColor: colors.white,
	borderBottom: `1px solid ${colors.slate[200]}`,
	gap: spacing[4],
};

const tenantStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	lineHeight: 1.1,
};

const searchBtnStyle: React.CSSProperties = {
	display: "inline-flex",
	alignItems: "center",
	gap: spacing[2],
	padding: `${spacing[2]} ${spacing[4]}`,
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: "9999px",
	backgroundColor: colors.slate[50],
	cursor: "pointer",
	fontSize: typography.size.sm,
	color: colors.slate[500],
	fontFamily: typography.fontFamily,
};

const kbdStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	color: colors.slate[400],
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.sm,
	padding: "1px 4px",
};

export default function AppHeader() {
	const { query } = useKBar();

	return (
		<header aria-label="App header" style={stripStyle}>
			<div style={tenantStyle} aria-label="Workspace">
				<span
					style={{
						fontSize: typography.size.sm,
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
						letterSpacing: "0.01em",
					}}
				>
					{TENANT.name}
				</span>
				<span
					style={{
						fontSize: typography.size.xs,
						color: colors.slate[400],
						fontWeight: typography.weight.medium,
						letterSpacing: "0.04em",
						textTransform: "uppercase",
					}}
				>
					{TENANT.subtitle}
				</span>
			</div>
			<button
				type="button"
				aria-label="Open search"
				style={searchBtnStyle}
				onClick={() => query.toggle()}
			>
				<Search size={14} />
				<span>Search</span>
				<span style={kbdStyle}>⌘K</span>
			</button>
		</header>
	);
}
