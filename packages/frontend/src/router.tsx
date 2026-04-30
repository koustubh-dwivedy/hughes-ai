import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { DashboardContextProvider } from "./context/DashboardContext";
import AppLayout from "./layout/AppLayout";
import ChatPage from "./pages/ChatPage";
import DepositsPage from "./pages/DepositsPage";
import ExecutiveSummaryPage from "./pages/ExecutiveSummaryPage";
import OfficersPage from "./pages/OfficersPage";
import PastDuePage from "./pages/PastDuePage";

const router = createBrowserRouter([
	{
		element: (
			<DashboardContextProvider>
				<AppLayout />
			</DashboardContextProvider>
		),
		children: [
			{ path: "/", element: <ExecutiveSummaryPage /> },
			{ path: "/deposits", element: <DepositsPage /> },
			{ path: "/past-due", element: <PastDuePage /> },
			{ path: "/officers", element: <OfficersPage /> },
			{ path: "/chat", element: <ChatPage /> },
		],
	},
]);

export default function Router() {
	return <RouterProvider router={router} />;
}
