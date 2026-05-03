// Plain-English definitions for credit-union metrics, indexed by metric id.
// Mirrors docs/metrics.md so the UI tooltip text and the docs stay aligned.
// Tooltips are intentionally a single sentence + a healthy-band hint where
// one exists — the goal is "a non-banker can read this and know what to
// think of the number," not "a regulator-grade definition."

export interface MetricDef {
	short: string;
	technical?: string;
	tooltip: string;
}

export const GLOSSARY: Record<string, MetricDef> = {
	total_loans: {
		short: "Total Loans",
		tooltip:
			"Outstanding loan balance across all active accounts as of the selected month. ↑ MoM = book is growing.",
	},
	mtd_loan_growth: {
		short: "MTD Loan Growth",
		tooltip:
			"Month-to-date net change in loan balance. Positive = book is growing this month.",
	},
	ytd_loan_growth: {
		short: "YTD Loan Growth",
		tooltip: "Year-to-date net change in loan balance, since January 1.",
	},
	total_deposits: {
		short: "Total Deposits",
		tooltip:
			"Total balance across all open deposit accounts (checking, savings, money market, CDs).",
	},
	mtd_deposit_growth: {
		short: "MTD Deposit Growth",
		tooltip:
			"Month-to-date net change in deposits. Positive = deposits are inflowing.",
	},
	ytd_deposit_growth: {
		short: "YTD Deposit Growth",
		tooltip: "Year-to-date net change in deposits, since January 1.",
	},
	past_due_ratio: {
		short: "Past Due Loans",
		technical: "Past Due Ratio (DPD ≥ 30)",
		tooltip:
			"Share of loan balance where the last scheduled payment is 30+ days late. Industry healthy band: under 1.5%. Above 2.5% is elevated.",
	},
	loan_to_deposit: {
		short: "Loan-to-Deposit",
		tooltip:
			"Loans ÷ deposits. Higher = more aggressively deployed. Typical credit-union range is 60–90%.",
	},
	core_deposit_ratio: {
		short: "Sticky-Deposit Share",
		technical: "Core Deposit Ratio",
		tooltip:
			"Share of deposits in checking + savings (vs CDs / money market). Higher = lower funding cost and less rate-sensitive.",
	},
	rate_spread: {
		short: "Margin",
		technical: "Loan Yield − Deposit Cost",
		tooltip:
			"Average loan interest rate minus average deposit interest rate. The bigger the gap, the more profitable the book. Below 200 bps is thin.",
	},
	past_due_total: {
		short: "Past Due Total",
		tooltip:
			"Total balance of loans 30+ days late as of this month. ↓ is good — fewer borrowers behind.",
	},
	nonaccrual_total: {
		short: "Loans Earning No Interest",
		technical: "Nonaccrual Balance",
		tooltip:
			"Loans where the credit union has stopped recognizing interest income — usually 90+ days late or seriously impaired. ↓ is good.",
	},
	watchlist_count: {
		short: "Loans Under Watch",
		technical: "Watchlist Count",
		tooltip:
			"Loans flagged by credit officers for closer monitoring. Not yet late, but showing risk signals. ↓ is good.",
	},
	nonperforming_balance: {
		short: "Non-Performing Balance",
		technical: "NPL Balance",
		tooltip:
			"Loans 90+ days late or on nonaccrual — the riskiest slice of the book. ↓ is good.",
	},
	account_count: {
		short: "Account Count",
		tooltip: "Number of open deposit accounts at the credit union.",
	},
	avg_balance: {
		short: "Avg Balance",
		tooltip:
			"Average deposit balance per account: total deposits ÷ account count.",
	},
	mtd_change: {
		short: "MTD Change",
		tooltip:
			"Month-to-date change: net deposit movement since the 1st of the month.",
	},
	ytd_change: {
		short: "YTD Change",
		tooltip: "Year-to-date change: net deposit movement since January 1.",
	},
	new_accounts: {
		short: "New Accounts",
		tooltip: "Deposit accounts opened during this month.",
	},
	closed_accounts: {
		short: "Closed Accounts",
		tooltip: "Deposit accounts closed during this month.",
	},
	total_loans_balance: {
		short: "Total Loans",
		tooltip:
			"Outstanding loan balance across all active accounts as of the selected month.",
	},
	avg_loan_balance: {
		short: "Avg Loan Balance",
		tooltip: "Total loans ÷ number of loan accounts.",
	},
};

export function metricDef(id: string): MetricDef | undefined {
	return GLOSSARY[id];
}
