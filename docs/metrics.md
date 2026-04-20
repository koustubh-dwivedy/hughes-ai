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

## Date Conventions

| Use case | Field to use |
|---|---|
| Origination date | `funded_at` from `funding_events` |
| Application date | `created_at` from `applications` |
| Balance as-of | `snapshot_date` from `loan_balances` |
| Delinquency as-of | `snapshot_date` from `delinquency_snapshots` |
| Payment date | `payment_date` from `payments` |
