# Hughes AI — Lending Metric Definitions

All metrics used in the NL engine are defined here. This file is the source of truth. The `packages/nl-engine/context/metrics.yaml` file mirrors these definitions in machine-readable form.

---

## Origination Metrics

### Origination Volume
- **Definition:** Total number of loan applications received in a period
- **Formula:** `COUNT(*) FROM applications WHERE created_at BETWEEN :start AND :end`
- **Source:** Origence LOS → `applications`
- **Caveats:** Includes all application statuses (pending, approved, declined, withdrawn). Filter by status for specific counts.

### Approval Rate
- **Definition:** Percentage of completed applications that were approved
- **Formula:** `COUNT(CASE WHEN status = 'approved' THEN 1 END) / COUNT(CASE WHEN status IN ('approved', 'declined') THEN 1 END)`
- **Source:** Origence LOS → `applications`, `approvals`
- **Caveats:** Excludes withdrawn and in-progress applications. Denominator is completed decisions only.

### Funding Rate
- **Definition:** Percentage of approved applications that were funded
- **Formula:** `COUNT(DISTINCT funding_events.application_id) / COUNT(CASE WHEN status = 'approved' THEN 1 END)`
- **Source:** Origence LOS → `approvals`, `funding_events`
- **Caveats:** A funding event must exist and have status = 'funded'. Approved-but-not-yet-funded applications are excluded.

### Average Loan Amount
- **Definition:** Mean funded loan amount in a period
- **Formula:** `AVG(funded_amount) FROM funding_events WHERE funded_at BETWEEN :start AND :end`
- **Source:** Origence LOS → `funding_events`
- **Caveats:** Uses funded amount, not requested amount. Use `funded_at` as the date field, not `created_at`.

### Origination Volume by Channel
- **Definition:** Origination count broken down by application channel
- **Source:** Origence LOS → `applications` JOIN `channels`
- **Channels:** branch, online, mobile, dealer, broker

### Origination Volume by Product Type
- **Definition:** Origination count broken down by loan product
- **Source:** Origence LOS → `applications` JOIN `product_types`

---

## Portfolio Metrics

### Portfolio Balance
- **Definition:** Total outstanding principal balance of all active booked loans
- **Formula:** `SUM(current_balance) FROM booked_loans WHERE status = 'active'`
- **Source:** Symitar → `booked_loans`, `loan_balances`
- **Caveats:** Uses most recent balance snapshot. Balance changes daily — always specify the as-of date.

### Delinquency Rate
- **Definition:** Percentage of active loans that are 30+ days past due
- **Formula:** `COUNT(CASE WHEN days_past_due >= 30 THEN 1 END) / COUNT(*) FROM delinquency_snapshots WHERE snapshot_date = :date AND loan_status = 'active'`
- **Source:** Symitar → `delinquency_snapshots`
- **Caveats:** Measured at snapshot date, not current. 30+, 60+, and 90+ buckets available. Use `snapshot_date` field — delinquency status is point-in-time.

### Delinquency Balance Rate
- **Definition:** Dollar-weighted delinquency rate (delinquent balance / total portfolio balance)
- **Formula:** `SUM(CASE WHEN days_past_due >= 30 THEN current_balance ELSE 0 END) / SUM(current_balance)`
- **Source:** Symitar → `delinquency_snapshots` JOIN `loan_balances`
- **Caveats:** More meaningful than count-based rate for risk assessment.

---

## Reconciliation Metrics

### LOS-to-Core Match Rate
- **Definition:** Percentage of funded LOS applications successfully matched to a booked Symitar loan
- **Formula:** `COUNT(matched) / COUNT(total_fundings) FROM reconciliation_bridge`
- **Source:** `reconciliation_bridge` view (joins Origence `funding_events` → Symitar `booked_loans`)
- **Caveats:** Unmatched records indicate either data lag or data quality issues. Match uses funding amount + date proximity + member ID.

---

## Dashboard KPI Metrics

These metrics power the pre-built dashboard views. Source tables are dbt marts in
`packages/dbt-models/models/marts/`.

### Total Deposits Balance
- **Definition:** Sum of current outstanding balance across all active deposit accounts
- **Formula:** `SUM(current_balance) FROM fct_deposits_monthly WHERE snapshot_date = :date AND status = 'active'`
- **Source:** `fct_deposits_monthly`
- **Caveats:** Point-in-time snapshot — always pair with `as_of_date`. Excludes closed accounts.

### Loan-to-Deposit Ratio
- **Definition:** Total loans balance divided by total deposits balance
- **Formula:** `total_loans_balance / total_deposits_balance`
- **Source:** `fct_executive_kpis`
- **Caveats:** Values above 1.0 indicate the CU is lending more than it holds in deposits. Regulatory guidance typically targets ≤ 0.80–0.90 for community CUs.

### Core Deposit Ratio
- **Definition:** Core deposits (checking + savings + money market) as a share of total deposits
- **Formula:** `SUM(balance WHERE product_type IN ('checking','savings','money_market')) / SUM(balance)`
- **Source:** `fct_deposits_monthly` JOIN `dim_deposit_product`
- **Caveats:** Higher ratios indicate more stable, lower-cost funding. CDs and brokered deposits are excluded from the numerator.

### Blended Past Due Ratio
- **Definition:** Dollar-weighted percentage of the total loan portfolio that is 30+ days past due, across all product types
- **Formula:** `SUM(balance WHERE days_past_due >= 30) / SUM(total_portfolio_balance)`
- **Source:** `fct_delinquency_monthly`
- **Caveats:** Cross-product blend — product-specific rates may differ significantly. Use delinquency drill-down for per-product analysis.

### Rate Spread
- **Definition:** Weighted average loan yield minus weighted average deposit cost
- **Formula:** `weighted_avg_loan_rate - weighted_avg_deposit_rate`
- **Source:** `fct_executive_kpis`
- **Caveats:** Simplified net interest margin proxy. Does not account for operating expenses, credit losses, or non-interest income.

### Nonaccrual Balance
- **Definition:** Outstanding principal balance on loans where interest accrual has been suspended due to credit deterioration
- **Formula:** `SUM(current_balance) FROM fct_loan_performance WHERE accrual_status = 'nonaccrual'`
- **Source:** `fct_loan_performance`
- **Caveats:** Typically triggered at 90+ DPD per NCUA guidance, but policy varies. Nonaccrual loans are a subset of — and often overlap with — NPL balance.

### Nonperforming Loan (NPL) Balance
- **Definition:** Outstanding balance of loans that are 90+ days past due or on nonaccrual status
- **Formula:** `SUM(current_balance) FROM fct_loan_performance WHERE days_past_due >= 90 OR accrual_status = 'nonaccrual'`
- **Source:** `fct_loan_performance`
- **Caveats:** NPL balance is the broadest risk indicator on the Past Due dashboard. An increasing NPL balance is adverse — the frontend negates the delta so an increase renders as a downward (red) movement.

---

## Date Conventions

| Use case | Field to use |
|---|---|
| Origination date | `funded_at` from `funding_events` |
| Application date | `created_at` from `applications` |
| Balance as-of | `snapshot_date` from `loan_balances` |
| Delinquency as-of | `snapshot_date` from `delinquency_snapshots` |
| Payment date | `payment_date` from `payments` |
| Dashboard as-of date | `?as_of_date` query param (defaults to latest snapshot) |
| Deposit balance as-of | `snapshot_date` from `fct_deposits_monthly` |
| Delinquency trend month | `month` from `fct_delinquency_monthly` |
