/**
 * RTK Query cache tag types. Each endpoint declares the tags it provides
 * or invalidates, so unrelated slices don't accidentally re-fetch on a
 * single mutation. Adding a new tag here is a deliberate decision —
 * keep it small.
 */
export const TAG_TYPES = [
	"DepositPortfolio",
	"PastDue",
	"OfficerBranch",
	"ExecutiveSummary",
	"Trust",
	"History",
	"Ask",
	"Thread",
	"ThreadList",
] as const;

export type TagType = (typeof TAG_TYPES)[number];
