import { NavLink, useLocation } from "react-router-dom";
import { colors, spacing, typography } from "../../theme/tokens";
import type { NavEntry } from "./types";

interface NavItemProps extends NavEntry {
	collapsed: boolean;
}

const ITEM_PADDING = `${spacing[3]} ${spacing[3]}`;

function activeStyle(isActive: boolean): React.CSSProperties {
	return {
		display: "flex",
		alignItems: "center",
		gap: spacing[3],
		padding: ITEM_PADDING,
		color: isActive ? colors.white : colors.slate[300],
		backgroundColor: isActive ? colors.indigo[600] : "transparent",
		textDecoration: "none",
		fontSize: typography.size.sm,
		fontWeight: isActive ? typography.weight.medium : typography.weight.normal,
		borderLeft: `2px solid ${isActive ? colors.indigo[500] : "transparent"}`,
		borderRadius: "0 4px 4px 0",
		transition: "background-color 150ms ease, color 150ms ease",
		overflow: "hidden",
		whiteSpace: "nowrap" as const,
		minHeight: 40,
	};
}

export default function NavItem({
	href,
	label,
	icon,
	collapsed,
}: NavItemProps) {
	const location = useLocation();
	const asOfDate = new URLSearchParams(location.search).get("as_of_date");
	const toPath = asOfDate
		? `${href}?as_of_date=${encodeURIComponent(asOfDate)}`
		: href;

	return (
		<NavLink
			to={toPath}
			title={collapsed ? label : undefined}
			style={({ isActive }) => activeStyle(isActive)}
		>
			<span
				style={{
					display: "flex",
					alignItems: "center",
					flexShrink: 0,
					fontSize: 16,
				}}
			>
				{icon}
			</span>
			{!collapsed && (
				<span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
					{label}
				</span>
			)}
		</NavLink>
	);
}
