import { ChevronLeft, ChevronRight, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import Logo from "../AppHeader/Logo";
import { colors, spacing } from "../../theme/tokens";
import NavItem from "./NavItem";
import { DASHBOARDS, DATA, INTELLIGENCE, SECTION_LABEL } from "./constants";
import type { CollapseState, SideNavProps } from "./types";

interface NavBodyProps {
	collapsed: boolean;
}

function NavBody({ collapsed }: NavBodyProps) {
	return (
		<div style={{ flex: 1, paddingTop: spacing[2], overflowY: "auto" }}>
			{!collapsed && <p style={SECTION_LABEL}>Intelligence</p>}
			{INTELLIGENCE.map((item) => (
				<NavItem key={item.href} {...item} collapsed={collapsed} />
			))}
			<div
				style={{
					height: 1,
					backgroundColor: colors.slate[700],
					margin: `${spacing[2]} 0`,
				}}
			/>
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
			{!collapsed && <p style={SECTION_LABEL}>Data</p>}
			{DATA.map((item) => (
				<NavItem key={item.href} {...item} collapsed={collapsed} />
			))}
		</div>
	);
}

type ViewportSize = "mobile" | "narrow" | "wide";

function classifyWidth(w: number): ViewportSize {
	if (w < 768) return "mobile";
	if (w < 1024) return "narrow";
	return "wide";
}

function useViewportSize() {
	const [size, setSize] = useState<ViewportSize>(() =>
		typeof window === "undefined" ? "wide" : classifyWidth(window.innerWidth),
	);
	useEffect(() => {
		const handler = () => setSize(classifyWidth(window.innerWidth));
		window.addEventListener("resize", handler);
		return () => window.removeEventListener("resize", handler);
	}, []);
	return size;
}

function isCollapsedFor(viewport: ViewportSize, state: CollapseState): boolean {
	if (viewport === "narrow") return true;
	return state === "collapsed";
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
	const viewport = useViewportSize();
	const isMobile = viewport === "mobile";

	const collapsed = isCollapsedFor(viewport, state);
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
						aria-label="Dismiss navigation"
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
								position: "relative",
								display: "flex",
								justifyContent: "center",
								alignItems: "center",
								padding: `${spacing[4]} ${spacing[3]}`,
								borderBottom: `1px solid ${colors.slate[700]}`,
							}}
						>
							<Logo variant="wordmark" onDark height={28} />
							<button
								type="button"
								aria-label="Close navigation"
								onClick={() => setDrawerOpen(false)}
								style={{
									position: "absolute",
									top: spacing[2],
									right: spacing[2],
									background: "none",
									border: "none",
									cursor: "pointer",
									color: colors.slate[300],
									padding: 4,
								}}
							>
								<X size={18} />
							</button>
						</div>
						<NavBody collapsed={false} />
					</nav>
				</dialog>
			)}
			<nav
				aria-label="primary"
				data-collapsed={String(collapsed)}
				style={{ ...navStyle, display: isMobile ? "none" : "flex" }}
				className="sidebar-desktop"
			>
				{collapsed ? (
					<div
						style={{
							display: "flex",
							flexDirection: "column",
							alignItems: "center",
							gap: spacing[1],
							padding: `${spacing[3]} 0`,
							borderBottom: `1px solid ${colors.slate[700]}`,
						}}
					>
						<Logo variant="icon" onDark height={40} />
						<button
							type="button"
							aria-label="Expand sidebar"
							onClick={() => setState("full")}
							style={{
								background: "none",
								border: "none",
								cursor: "pointer",
								color: colors.slate[400],
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								padding: 2,
							}}
						>
							<ChevronRight size={14} />
						</button>
					</div>
				) : (
					<div
						style={{
							position: "relative",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							padding: `${spacing[4]} ${spacing[3]}`,
							borderBottom: `1px solid ${colors.slate[700]}`,
						}}
					>
						<Logo variant="wordmark" onDark height={28} />
						<button
							type="button"
							aria-label="Collapse sidebar"
							onClick={() => setState("collapsed")}
							style={{
								position: "absolute",
								top: spacing[2],
								right: spacing[2],
								background: "none",
								border: "none",
								cursor: "pointer",
								color: colors.slate[400],
								padding: 2,
								display: "flex",
								alignItems: "center",
							}}
						>
							<ChevronLeft size={14} />
						</button>
					</div>
				)}
				<NavBody collapsed={collapsed} />
			</nav>
		</>
	);
}
