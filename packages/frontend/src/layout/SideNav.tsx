import { NavLink } from "react-router-dom";
import { colors, spacing, typography } from "../theme/tokens";

const NAV_ITEMS = [
	{ label: "Executive Summary", href: "/dashboards/executive" },
	{ label: "Deposit Portfolio", href: "/dashboards/deposits" },
	{ label: "Past Due", href: "/dashboards/past-due" },
	{ label: "Officer/Branch", href: "/dashboards/officer-branch" },
	{ label: "Chat", href: "/chat" },
] as const;

export default function SideNav() {
	return (
		<nav
			aria-label="primary"
			style={{
				width: 240,
				minWidth: 240,
				height: "100vh",
				backgroundColor: colors.slate[800],
				display: "flex",
				flexDirection: "column",
				overflowY: "auto",
			}}
		>
			<div
				style={{
					padding: `${spacing[6]} ${spacing[4]}`,
					color: colors.white,
					fontWeight: typography.weight.bold,
					fontSize: typography.size.lg,
					borderBottom: `1px solid ${colors.slate[700]}`,
				}}
			>
				Hughes AI
			</div>
			{NAV_ITEMS.map(({ label, href }) => (
				<NavLink
					key={href}
					to={href}
					style={({ isActive }) => ({
						display: "block",
						padding: `${spacing[3]} ${spacing[4]}`,
						color: isActive ? colors.white : colors.slate[300],
						backgroundColor: isActive ? colors.slate[900] : "transparent",
						textDecoration: "none",
						fontSize: typography.size.sm,
						fontWeight: isActive
							? typography.weight.medium
							: typography.weight.normal,
					})}
				>
					{label}
				</NavLink>
			))}
		</nav>
	);
}
