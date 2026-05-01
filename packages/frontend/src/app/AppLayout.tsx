import { Outlet } from "react-router-dom";
import SideNav from "./SideNav";

export default function AppLayout() {
	return (
		<div style={{ display: "flex", height: "100vh" }}>
			<SideNav />
			<main style={{ flex: 1, overflow: "auto", padding: "2rem" }}>
				<Outlet />
			</main>
		</div>
	);
}
