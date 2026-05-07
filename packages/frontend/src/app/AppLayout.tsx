import { Outlet, useLocation } from "react-router-dom";
import { RouteFade } from "../ui/primitives/motion";
import AppHeader from "./AppHeader";
import SideNav from "./SideNav";

export default function AppLayout() {
	const { pathname } = useLocation();
	const isChatSurface = pathname.startsWith("/intelligence");
	// The chat surface manages its own internal scroll on the conversation
	// pane; the dashboards expect the main column to scroll itself.
	const mainStyle: React.CSSProperties = isChatSurface
		? {
				flex: 1,
				minHeight: 0,
				overflow: "hidden",
				position: "relative",
				display: "flex",
				flexDirection: "column",
			}
		: {
				flex: 1,
				overflow: "auto",
				padding: "2rem",
				position: "relative",
			};
	return (
		<div style={{ display: "flex", height: "100vh" }}>
			<SideNav />
			<div
				style={{
					flex: 1,
					display: "flex",
					flexDirection: "column",
					overflow: "hidden",
					minHeight: 0,
				}}
			>
				<AppHeader />
				<main style={mainStyle}>
					<RouteFade>
						<Outlet />
					</RouteFade>
				</main>
			</div>
		</div>
	);
}
