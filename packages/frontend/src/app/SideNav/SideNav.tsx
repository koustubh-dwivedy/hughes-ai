import {
	ChevronLeft,
	ChevronRight,
	HelpCircle,
	Menu,
	Settings,
	UserCircle2,
	X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { colors, spacing, typography } from "../../theme/tokens";
import NavItem from "./NavItem";
import { DASHBOARDS, SECTION_LABEL, TOOLS } from "./constants";
import type { CollapseState, SideNavProps } from "./types";

interface NavBodyProps {
	collapsed: boolean;
}

function NavBody({ collapsed }: NavBodyProps) {
	return (
		<div style={{ flex: 1, paddingTop: spacing[2] }}>
			{!collapsed && <p style={SECTION_LABEL}>Dashboards</p>}
			{DASHBOARDS.map((item) => (
				<NavItem key={item.href} {...item} collapsed={collapsed} />
			))}
			<div
				style={{
					height: 1,
					backgroundColor: colors.slate[700],
					margin: `${spacing[2]} 0`,
				}}
			/>
			{!collapsed && <p style={SECTION_LABEL}>Tools</p>}
			{TOOLS.map((item) => (
				<NavItem key={item.href} {...item} collapsed={collapsed} />
			))}
		</div>
	);
}

interface BottomRailProps {
	collapsed: boolean;
}

function BottomRail({ collapsed }: BottomRailProps) {
	const btnStyle: React.CSSProperties = {
		background: "none",
		border: "none",
		cursor: "pointer",
		color: colors.slate[400],
	};
	return (
		<div
			style={{
				display: "flex",
				justifyContent: collapsed ? "center" : "space-around",
				padding: `${spacing[3]} ${spacing[2]}`,
				borderTop: `1px solid ${colors.slate[700]}`,
				gap: spacing[1],
			}}
		>
			<button type="button" aria-label="User profile" style={btnStyle}>
				<UserCircle2 size={20} />
			</button>
			{!collapsed && (
				<>
					<button type="button" aria-label="Settings" style={btnStyle}>
						<Settings size={20} />
					</button>
					<button type="button" aria-label="Help" style={btnStyle}>
						<HelpCircle size={20} />
					</button>
				</>
			)}
		</div>
	);
}

function useMobileViewport() {
	const [isMobile, setIsMobile] = useState(
		() => typeof window !== "undefined" && window.innerWidth < 768,
	);
	useEffect(() => {
		const handler = () => setIsMobile(window.innerWidth < 768);
		window.addEventListener("resize", handler);
		return () => window.removeEventListener("resize", handler);
	}, []);
	return isMobile;
}

function HamburgerButton({
	expanded,
	onClick,
	visible,
}: { expanded: boolean; onClick: () => void; visible: boolean }) {
	return (
		<button
			type="button"
			aria-label="Open navigation"
			aria-expanded={expanded}
			data-testid="hamburger"
			onClick={onClick}
			className="sidebar-hamburger"
			style={{
				position: "fixed",
				top: spacing[3],
				left: spacing[3],
				zIndex: 200,
				background: colors.slate[800],
				border: "none",
				borderRadius: 6,
				padding: spacing[2],
				cursor: "pointer",
				color: colors.white,
				display: visible ? "flex" : "none",
			}}
		>
			<Menu size={20} />
		</button>
	);
}

export default function SideNav({ defaultCollapsed = false }: SideNavProps) {
	const [state, setState] = useState<CollapseState>(
		defaultCollapsed ? "collapsed" : "full",
	);
	const [drawerOpen, setDrawerOpen] = useState(false);
	const isMobile = useMobileViewport();

	const collapsed = state === "collapsed";
	const width = collapsed ? 56 : 240;

	const navStyle: React.CSSProperties = {
		width,
		minWidth: width,
		height: "100vh",
		backgroundColor: colors.slate[800],
		display: "flex",
		flexDirection: "column",
		overflowY: "auto",
		overflowX: "hidden",
		transition: "width 200ms ease, min-width 200ms ease",
		flexShrink: 0,
	};

	const wordmarkStyle: React.CSSProperties = {
		color: colors.white,
		fontWeight: typography.weight.bold,
		fontSize: typography.size.base,
	};

	return (
		<>
			<HamburgerButton
				expanded={drawerOpen}
				onClick={() => setDrawerOpen(true)}
				visible={isMobile}
			/>
			{drawerOpen && (
				<dialog
					aria-label="Navigation drawer"
					open
					style={{
						position: "fixed",
						inset: 0,
						zIndex: 300,
						display: "flex",
						border: "none",
						padding: 0,
						margin: 0,
						maxWidth: "none",
						maxHeight: "none",
						width: "100%",
						height: "100%",
						background: "none",
					}}
				>
					<button
						type="button"
						aria-label="Close navigation"
						onClick={() => setDrawerOpen(false)}
						style={{
							position: "absolute",
							inset: 0,
							background: "rgba(0,0,0,0.5)",
							border: "none",
							cursor: "pointer",
							width: "100%",
						}}
					/>
					<nav
						aria-label="primary"
						data-collapsed="false"
						style={{
							...navStyle,
							width: 240,
							minWidth: 240,
							position: "relative",
							zIndex: 1,
						}}
					>
						<div
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
								padding: `${spacing[4]} ${spacing[3]}`,
								borderBottom: `1px solid ${colors.slate[700]}`,
							}}
						>
							<span style={wordmarkStyle}>Hughes AI</span>
							<button
								type="button"
								aria-label="Close navigation"
								onClick={() => setDrawerOpen(false)}
								style={{
									background: "none",
									border: "none",
									cursor: "pointer",
									color: colors.slate[300],
								}}
							>
								<X size={18} />
							</button>
						</div>
						<NavBody collapsed={false} />
						<BottomRail collapsed={false} />
					</nav>
				</dialog>
			)}
			<nav
				aria-label="primary"
				data-collapsed={String(collapsed)}
				style={{ ...navStyle, display: isMobile ? "none" : "flex" }}
				className="sidebar-desktop"
			>
				<div
					style={{
						display: "flex",
						alignItems: "center",
						justifyContent: collapsed ? "center" : "space-between",
						padding: collapsed
							? `${spacing[4]} 0`
							: `${spacing[4]} ${spacing[3]}`,
						borderBottom: `1px solid ${colors.slate[700]}`,
					}}
				>
					{!collapsed && <span style={wordmarkStyle}>Hughes AI</span>}
					<button
						type="button"
						aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
						onClick={() =>
							setState((s) => (s === "full" ? "collapsed" : "full"))
						}
						style={{
							background: "none",
							border: "none",
							cursor: "pointer",
							color: colors.slate[300],
							display: "flex",
							alignItems: "center",
						}}
					>
						{collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
					</button>
				</div>
				<NavBody collapsed={collapsed} />
				{!collapsed && (
					<div
						style={{
							padding: `${spacing[2]} ${spacing[3]}`,
							fontSize: typography.size.xs,
							color: colors.slate[500],
							textAlign: "center",
						}}
					>
						<span
							style={{
								display: "inline-flex",
								alignItems: "center",
								gap: spacing[1],
								padding: `2px ${spacing[2]}`,
								border: `1px solid ${colors.slate[600]}`,
								borderRadius: 4,
							}}
						>
							⌘K
						</span>
					</div>
				)}
				<BottomRail collapsed={collapsed} />
			</nav>
		</>
	);
}
