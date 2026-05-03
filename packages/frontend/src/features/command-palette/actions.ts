import type { Action } from "kbar";

export const defaultActions: Action[] = [
	{
		id: "nav-executive",
		name: "Executive Summary",
		keywords: "executive summary dashboard kpis overview",
		section: "Dashboards",
		perform: () => {
			window.location.href = "/dashboards/executive";
		},
	},
	{
		id: "nav-deposits",
		name: "Deposit Portfolio",
		keywords: "deposit portfolio dashboard savings",
		section: "Dashboards",
		perform: () => {
			window.location.href = "/dashboards/deposits";
		},
	},
	{
		id: "nav-past-due",
		name: "Past Due",
		keywords: "past due delinquency loans overdue",
		section: "Dashboards",
		perform: () => {
			window.location.href = "/dashboards/past-due";
		},
	},
	{
		id: "nav-officers",
		name: "Officer & Branch",
		keywords: "officer branch performance team",
		section: "Dashboards",
		perform: () => {
			window.location.href = "/dashboards/officer-branch";
		},
	},
	{
		id: "nav-intelligence",
		name: "Ask Hughes",
		keywords: "ask question intelligence nl natural language search chat data",
		section: "Intelligence",
		perform: () => {
			window.location.href = "/intelligence";
		},
	},
	{
		id: "nav-data-sources",
		name: "Sources & Freshness",
		keywords:
			"data sources freshness reconciliation trust caveats origence symitar",
		section: "Data",
		perform: () => {
			window.location.href = "/data/sources";
		},
	},
];
