import {
	Navigate,
	RouterProvider,
	createBrowserRouter,
} from "react-router-dom";
import AppLayout from "./app/AppLayout";
import DataSourcesPage from "./pages/DataSourcesPage";
import DepositsPage from "./pages/DepositsPage";
import ExecutiveSummaryPage from "./pages/ExecutiveSummaryPage";
import IntelligencePage from "./pages/IntelligencePage";
import OfficersPage from "./pages/OfficersPage";
import PastDuePage from "./pages/PastDuePage";
import { DashboardContextProvider } from "./shared/context/DashboardContext";

const router = createBrowserRouter([
	{
		element: (
			<DashboardContextProvider>
				<AppLayout />
			</DashboardContextProvider>
		),
		children: [
			{
				path: "/",
				element: <Navigate to="/dashboards/executive" replace />,
			},
			{ path: "/dashboards/executive", element: <ExecutiveSummaryPage /> },
			{ path: "/dashboards/deposits", element: <DepositsPage /> },
			{ path: "/dashboards/past-due", element: <PastDuePage /> },
			{ path: "/dashboards/officer-branch", element: <OfficersPage /> },
			{ path: "/intelligence", element: <IntelligencePage /> },
			{ path: "/chat", element: <Navigate to="/intelligence" replace /> },
			{ path: "/data/sources", element: <DataSourcesPage /> },
		],
	},
]);

export default function Router() {
	return <RouterProvider router={router} />;
}
