# Hughes AI — Dashboard Reference

Four pre-built dashboards provide structured lending analytics. Each is backed by a
dedicated dbt mart and a typed API endpoint. See `docs/decisions/0001-dashboards-fetch-strategy.md`
for the architectural rationale.

---

## Navigation

All dashboards live under the `/dashboards/` path prefix. The root `/` redirects to
Executive Summary. The left-nav (`SideNav`) highlights the active route via `aria-current="page"`.

| Route | Dashboard |
|---|---|
| `/dashboards/executive` | Executive Summary (default landing) |
| `/dashboards/deposits` | Deposit Portfolio |
| `/dashboards/past-due` | Past Due |
| `/dashboards/officer-branch` | Officer / Branch Loans |
| `/chat` | NL Chat |

---

## Executive Summary

**Route:** `/dashboards/executive`
**API:** `GET /api/dashboards/executive-summary?as_of_date=YYYY-MM-DD`
**Backing marts:** `fct_executive_kpis`, `fct_loans_monthly`, `fct_delinquency_monthly`

### KPI tiles (9)

| Label | Field | Format |
|---|---|---|
| Total Loans | `total_loans_balance` | $M |
| Total Deposits | `total_deposits_balance` | $M |
| MTD Loan Growth | `monthly_loan_growth` | $M |
| YTD Loan Growth | `ytd_loan_growth` | $M |
| MTD Deposit Growth | `monthly_deposit_growth` | $M |
| YTD Deposit Growth | `ytd_deposit_growth` | $M |
| Past Due Ratio | `blended_past_due_ratio` | % |
| Loan-to-Deposit | `loan_to_deposit_ratio` | % |
| Core Deposit Ratio | `core_deposit_ratio` | % |

### Charts

| Panel | Type | Data source |
|---|---|---|
| Loans & Rate Spread (13 mo.) | Combo (bar + line) | `kpi_trend_13_months` |
| MTD Growth ($M) | Stacked bar | `monthly_loan_growth`, `monthly_deposit_growth` |
| Past Due Aging | Bar | `past_due_aging` (4 DPD buckets) |
| Past Due Ratio Trend (13 mo.) | Line | `kpi_trend_13_months.blended_past_due_ratio` |

---

## Deposit Portfolio

**Route:** `/dashboards/deposits`
**API:** `GET /api/dashboards/deposit-portfolio?as_of_date=YYYY-MM-DD`
**Backing marts:** `fct_deposits_monthly`, `dim_deposit_product`, `dim_member`

### KPI tiles (5)

| Label | Field | Format |
|---|---|---|
| Total Deposits | `total_deposits` | $M |
| MTD Change | `mtd_change` | $M |
| YTD Change | `ytd_change` | $M |
| Account Count | `account_count` | integer |
| Avg Balance | `avg_balance_per_customer` | $ |

### Charts

| Panel | Type | Data source |
|---|---|---|
| Deposit Mix | Donut | `deposit_mix` |
| Deposits by Branch | Stacked bar | `deposits_by_branch` |
| Change by Product ($M) | Waterfall | `change_by_product` |
| New vs. Closed Accounts | Stacked bar | `new_vs_closed_accounts` |

### Table

Top-25 depositors: member name, balance, portfolio share.

---

## Past Due

**Route:** `/dashboards/past-due`
**API:** `GET /api/dashboards/past-due?as_of_date=YYYY-MM-DD`
**Backing marts:** `fct_delinquency_monthly`, `fct_loan_performance`, `dim_officer`

### KPI tiles (4)

Delta values are **negated** before display — an increase in past-due metrics renders
as a downward (red) movement to communicate that growth is adverse.

| Label | Field | Format |
|---|---|---|
| Past Due Total | `past_due_total` | $M |
| Nonaccrual | `nonaccrual_total` | $M |
| Watchlist | `watchlist_count` | integer |
| NPL Balance | `nonperforming_balance` | $M |

### Charts

| Panel | Type | Data source |
|---|---|---|
| Past Due by Officer | Bar | `past_due_by_officer` |
| Delinquency Trend (13 mo.) | Stacked bar | `delinquency_trend_13_months` (30-59, 60-89, 90+ DPD) |
| Past Due Ratio Trend | Line | `past_due_ratio_trend` |

---

## Officer / Branch Loans

**Route:** `/dashboards/officer-branch`
**API:** `GET /api/dashboards/officer-branch?as_of_date=YYYY-MM-DD`
**Backing marts:** `fct_loans_monthly`, `fct_loan_lifecycle_events`, `dim_officer`, `dim_loan`

> **Demo data only** — borrower names in the top-25 table are synthetic and do not
> represent real members. A persistent banner (`role="note"`) is always visible.

### KPI tiles (3)

| Label | Field | Format |
|---|---|---|
| Total Loans | `total_loans` | $M |
| Account Count | `account_count` | integer |
| Avg Loan Balance | `avg_loan_balance` | $ |

### Charts

| Panel | Type | Data source |
|---|---|---|
| Loan Mix | Donut | `loan_mix_donut` |
| Single-Loan Customers by Type | Bar | `single_loan_customers_by_type` |
| MTD Change by Type ($M) | Waterfall | `change_by_type_waterfall` |
| Balance vs. Rate | Combo (bar + line) | `combo_balance_rate` |

### Table

Top-25 borrowers: synthetic member name, balance, portfolio share.

---

## Response envelope

All dashboard endpoints return:

```json
{
  "data": { ... },
  "as_of_date": "YYYY-MM-DD",
  "generated_at": "ISO-8601 timestamp",
  "audit_id": "uuid"
}
```

`audit_id` links to the query audit log. `generated_at` is used by the frontend to
enforce the 5-minute client-side cache TTL (see ADR-0001).
