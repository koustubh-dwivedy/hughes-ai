import { Outlet } from "react-router-dom";
import AppHeader from "./AppHeader";
import SideNav from "./SideNav";

export default function AppLayout() {
	return (
		<div style={{ display: "flex", height: "100vh" }}>
			<SideNav />
			<div
				style={{
					flex: 1,
					display: "flex",
					flexDirection: "column",
					overflow: "hidden",
				}}
			>
				<AppHeader />
				<main style={{ flex: 1, overflow: "auto", padding: "2rem" }}>
					<Outlet />
				</main>
			</div>
		</div>
	);
}
