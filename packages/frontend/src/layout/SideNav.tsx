import { Link, useLocation } from "react-router-dom";
import { colors, spacing, typography } from "../theme/tokens";

const NAV_ITEMS = [
	{ label: "Executive Summary", href: "/" },
	{ label: "Deposit Portfolio", href: "/deposits" },
	{ label: "Past Due", href: "/past-due" },
	{ label: "Officer/Branch", href: "/officers" },
	{ label: "Chat", href: "/chat" },
] as const;

export default function SideNav() {
	const { pathname } = useLocation();
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
			{NAV_ITEMS.map(({ label, href }) => {
				const active =
					href === "/" ? pathname === "/" : pathname.startsWith(href);
				return (
					<Link
						key={href}
						to={href}
						aria-current={active ? "page" : undefined}
						style={{
							display: "block",
							padding: `${spacing[3]} ${spacing[4]}`,
							color: active ? colors.white : colors.slate[300],
							backgroundColor: active ? colors.slate[900] : "transparent",
							textDecoration: "none",
							fontSize: typography.size.sm,
							fontWeight: active
								? typography.weight.medium
								: typography.weight.normal,
						}}
					>
						{label}
					</Link>
				);
			})}
		</nav>
	);
}
