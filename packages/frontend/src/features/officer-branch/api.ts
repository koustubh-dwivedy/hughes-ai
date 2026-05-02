import { baseApi } from "../../shared/api/client";
import type {
	DashboardEnvelope,
	OfficerBranchData,
} from "../../shared/api/dashboardApi";

export interface OfficerBranchArg {
	asOfDate?: string;
	branchId?: number;
	officerId?: string;
	tab?: string;
}

function toQueryParams(arg: OfficerBranchArg): Record<string, string> {
	const out: Record<string, string> = {};
	if (arg.asOfDate) out.as_of_date = arg.asOfDate;
	if (arg.branchId !== undefined) out.branch_id = String(arg.branchId);
	if (arg.officerId) out.officer_id = arg.officerId;
	if (arg.tab) out.tab = arg.tab;
	return out;
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getOfficerBranch: build.query<OfficerBranchData, OfficerBranchArg>({
			query: (arg = {}) => ({
				url: "/dashboards/officer-branch",
				params: toQueryParams(arg),
			}),
			transformResponse: (env: DashboardEnvelope<OfficerBranchData>) =>
				env.data,
			providesTags: ["OfficerBranch"],
		}),
	}),
	overrideExisting: false,
});

export const { useGetOfficerBranchQuery } = slice;

export function useOfficerBranch(arg: OfficerBranchArg = {}) {
	const result = useGetOfficerBranchQuery(arg);
	return {
		data: result.data ?? null,
		loading: result.isLoading,
		isError: result.isError,
	};
}
