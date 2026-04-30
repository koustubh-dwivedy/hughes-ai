/** Wrapper returned by every /api/dashboards/* endpoint. */
export interface DashboardEnvelope<T> {
	data: T;
	as_of_date: string;
	generated_at: string;
	audit_id: string;
}

/** Params accepted by any dashboard fetcher. */
export interface DashboardParams {
	asOfDate?: string;
	branchId?: number;
	officerId?: string;
	tab?: string;
}

// ── Deposit Portfolio ─────────────────────────────────────────────────────────

export interface TopDeposit {
	member_name: string;
	balance: number;
	share_pct: number;
}
export interface BranchBalance {
	branch_name: string;
	balance: number;
}
export interface ProductBalance {
	product: string;
	balance: number;
	share_pct: number;
}
export interface ProductDelta {
	product: string;
	delta: number;
}
export interface AccountActivity {
	count: number;
	amount: number;
}
export interface NewVsClosed {
	opened: AccountActivity;
	closed: AccountActivity;
}

export interface DepositPortfolioData {
	total_deposits: number;
	mtd_change: number;
	ytd_change: number;
	avg_balance_per_customer: number;
	account_count: number;
	top_25_deposits: TopDeposit[];
	deposits_by_branch: BranchBalance[];
	deposit_mix: ProductBalance[];
	change_by_product: ProductDelta[];
	new_vs_closed_accounts: NewVsClosed;
}

// ── Past Due ─────────────────────────────────────────────────────────────────

export interface OfficerDelinquency {
	officer_name: string;
	balance: number;
	count: number;
}
export interface DelinquencyTrendMonth {
	month: string;
	bucket_30_59: number;
	bucket_60_89: number;
	bucket_90_plus: number;
}
export interface PastDueRatioPoint {
	month: string;
	ratio: number;
}

export interface PastDueData {
	past_due_total: number;
	past_due_total_delta: number;
	nonaccrual_total: number;
	nonaccrual_total_delta: number;
	watchlist_count: number;
	watchlist_count_delta: number;
	nonperforming_balance: number;
	nonperforming_balance_delta: number;
	past_due_by_officer: OfficerDelinquency[];
	delinquency_trend_13_months: DelinquencyTrendMonth[];
	past_due_ratio_trend: PastDueRatioPoint[];
}

// ── Officer / Branch ──────────────────────────────────────────────────────────

export interface WatchlistTrendPoint {
	month: string;
	count: number;
	balance: number;
}

export interface LifecycleTabRow {
	period: string;
	product_type: string;
	count: number;
	amount: number;
}

export interface TopBorrower {
	member_name: string;
	balance: number;
	share_pct: number;
}
export interface LoanMixItem {
	product: string;
	balance: number;
	share_pct: number;
}
export interface WaterfallStep {
	product: string;
	delta: number;
}
export interface SingleLoanCount {
	product: string;
	count: number;
}
export interface ComboBalanceRate {
	product: string;
	balance: number;
	weighted_avg_rate: number;
}

export interface OfficerBranchData {
	total_loans: number;
	account_count: number;
	avg_loan_balance: number;
	top_25_borrowers: TopBorrower[];
	loan_mix_donut: LoanMixItem[];
	change_by_type_waterfall: WaterfallStep[];
	single_loan_customers_by_type: SingleLoanCount[];
	combo_balance_rate: ComboBalanceRate[];
	watchlist_trend: WatchlistTrendPoint[];
	tab_data: LifecycleTabRow[] | null;
}

// ── Executive Summary ─────────────────────────────────────────────────────────

export interface KpiTrendPoint {
	month: string;
	total_loans_balance: number;
	total_deposits_balance: number;
	blended_past_due_ratio: number;
	rate_spread: number;
}
export interface PastDueAgingBucket {
	bucket: string;
	balance: number;
	loan_count: number;
}

export interface ExecutiveSummaryData {
	total_loans_balance: number;
	total_deposits_balance: number;
	loan_to_deposit_ratio: number;
	core_deposit_ratio: number;
	blended_past_due_ratio: number;
	monthly_loan_growth: number;
	monthly_deposit_growth: number;
	ytd_loan_growth: number;
	ytd_deposit_growth: number;
	weighted_avg_loan_rate: number;
	weighted_avg_deposit_rate: number;
	rate_spread: number;
	kpi_trend_13_months: KpiTrendPoint[];
	past_due_aging: PastDueAgingBucket[];
}
