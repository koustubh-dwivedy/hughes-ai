import { createContext, useCallback, useContext } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

export interface DashboardContextValue {
	asOfDate: string | undefined;
	setAsOfDate: (date: string | undefined) => void;
	latestAvailable: string | undefined;
}

const DashboardContext = createContext<DashboardContextValue>({
	asOfDate: undefined,
	setAsOfDate: () => undefined,
	latestAvailable: undefined,
});

export function DashboardContextProvider({
	children,
}: { children: ReactNode }) {
	const [searchParams, setSearchParams] = useSearchParams();
	const asOfDate = searchParams.get("as_of_date") ?? undefined;

	const setAsOfDate = useCallback(
		(date: string | undefined) => {
			setSearchParams((prev) => {
				const next = new URLSearchParams(prev);
				if (date) {
					next.set("as_of_date", date);
				} else {
					next.delete("as_of_date");
				}
				return next;
			});
		},
		[setSearchParams],
	);

	return (
		<DashboardContext.Provider
			value={{ asOfDate, setAsOfDate, latestAvailable: undefined }}
		>
			{children}
		</DashboardContext.Provider>
	);
}

export function useDashboardContext(): DashboardContextValue {
	return useContext(DashboardContext);
}
