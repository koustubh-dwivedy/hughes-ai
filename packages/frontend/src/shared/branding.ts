// Synthetic-tenant identity. The product is a single-CU demo running on
// generated Origence + Symitar data — naming the workspace makes it
// obvious to viewers that the data isn't real and gives the dashboards
// a credible backdrop instead of a blank "Hughes AI" wordmark.

export const TENANT = {
	name: "Cascade Federal Credit Union",
	shortName: "Cascade FCU",
	subtitle: "synthetic demo data",
} as const;
