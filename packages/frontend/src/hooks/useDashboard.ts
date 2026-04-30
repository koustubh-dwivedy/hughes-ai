import { useCallback, useEffect, useState } from "react";
import type { DashboardEnvelope, DashboardParams } from "../lib/dashboardApi";

export interface UseDashboardResult<T> {
	data: T | null;
	loading: boolean;
	error: string | null;
	refetch: () => void;
}

type Fetcher<T> = (params?: DashboardParams) => Promise<DashboardEnvelope<T>>;

export function useDashboard<T>(
	fetcher: Fetcher<T>,
	params?: DashboardParams,
): UseDashboardResult<T> {
	const [data, setData] = useState<T | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [refetchCount, setRefetchCount] = useState(0);

	const refetch = useCallback(() => setRefetchCount((c) => c + 1), []);

	// Destructure to primitives so exhaustive-deps can track them individually.
	const asOfDate = params?.asOfDate;
	const branchId = params?.branchId;
	const officerId = params?.officerId;
	const tab = params?.tab;

	// biome-ignore lint/correctness/useExhaustiveDependencies: refetchCount is a version counter that triggers manual re-fetches without being read inside the effect
	useEffect(() => {
		const ctrl = new AbortController();
		setLoading(true);
		setError(null);

		fetcher({ asOfDate, branchId, officerId, tab })
			.then((env) => {
				if (!ctrl.signal.aborted) {
					setData(env.data);
					setLoading(false);
				}
			})
			.catch((err: unknown) => {
				if (!ctrl.signal.aborted) {
					setError(err instanceof Error ? err.message : "Unknown error");
					setLoading(false);
				}
			});

		return () => {
			ctrl.abort();
		};
	}, [fetcher, asOfDate, branchId, officerId, tab, refetchCount]);

	return { data, loading, error, refetch };
}
