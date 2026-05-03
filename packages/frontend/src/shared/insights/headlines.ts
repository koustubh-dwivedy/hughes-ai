// Per-dashboard "executive read" generators. Each returns a Headline whose
// lede is one sentence answering the question the user opens the page asking
// — and three callouts (strength / watch / context) so a non-expert can leave
// with a story instead of a wall of numbers. All rules are deterministic so
// the demo is reproducible. No LLM call.

import type {
	DepositPortfolioData,
	ExecutiveSummaryData,
	OfficerBranchData,
	PastDueData,
} from "../api/dashboardApi";
import {
	dirArrow,
	fmtMoney,
	fmtPct,
	productLabel,
	type HeadlineCalloutTone,
	type HeadlineTone,
} from "./headlineUtils";

export interface HeadlineCallout {
	tone: HeadlineCalloutTone;
	label: string;
	body: string;
}

export interface Headline {
	lede: string;
	callouts: HeadlineCallout[];
	tone: HeadlineTone;
}

function overallTone(callouts: HeadlineCallout[]): HeadlineTone {
	return callouts.some((c) => c.tone === "warn") ? "warn" : "info";
}

// ── Executive Summary ────────────────────────────────────────────────────────

export function executiveHeadline(d: ExecutiveSummaryData): Headline {
	const ratioPct = d.blended_past_due_ratio * 100;
	const ratioPriorPct =
		d.kpi_trend_13_months.length >= 2
			? d.kpi_trend_13_months[d.kpi_trend_13_months.length - 2]
					.blended_past_due_ratio * 100
			: ratioPct;
	const ratioDeltaPp = ratioPct - ratioPriorPct;

	const lede =
		`Loans ${dirArrow(d.monthly_loan_growth)} ${fmtMoney(Math.abs(d.monthly_loan_growth))} MoM, ` +
		`deposits ${dirArrow(d.monthly_deposit_growth)} ${fmtMoney(Math.abs(d.monthly_deposit_growth))}. ` +
		`Past-due ratio at ${fmtPct(ratioPct)} ` +
		(ratioDeltaPp >= 0
			? `(↑ ${fmtPct(Math.abs(ratioDeltaPp), 2)} pp)`
			: `(↓ ${fmtPct(Math.abs(ratioDeltaPp), 2)} pp)`) +
		".";

	const callouts: HeadlineCallout[] = [];

	if (d.monthly_loan_growth > 0 || d.monthly_deposit_growth > 0) {
		const lead =
			d.monthly_loan_growth >= d.monthly_deposit_growth
				? `Loan book added ${fmtMoney(Math.abs(d.monthly_loan_growth))} this month.`
				: `Deposits added ${fmtMoney(Math.abs(d.monthly_deposit_growth))} this month.`;
		callouts.push({ tone: "success", label: "Strength", body: lead });
	} else {
		callouts.push({
			tone: "info",
			label: "Steady",
			body: "Both loans and deposits roughly flat MoM.",
		});
	}

	if (ratioPct > 1.5 || ratioDeltaPp > 0.1) {
		callouts.push({
			tone: "warn",
			label: "Watch",
			body:
				ratioPct > 1.5
					? `Past-due at ${fmtPct(ratioPct)} — above the 1.5% healthy band.`
					: `Past-due ticked up ${fmtPct(Math.abs(ratioDeltaPp), 2)} pp from last month.`,
		});
	} else {
		callouts.push({
			tone: "success",
			label: "Risk",
			body: `Past-due ${fmtPct(ratioPct)} is inside the healthy band.`,
		});
	}

	const spreadPct = d.rate_spread * 100;
	callouts.push({
		tone: spreadPct < 2 ? "warn" : "info",
		label: "Margin",
		body:
			spreadPct < 2
				? `Spread ${fmtPct(spreadPct)} — net interest margin is thin.`
				: `Loan yield − deposit cost = ${fmtPct(spreadPct)}.`,
	});

	return { lede, callouts, tone: overallTone(callouts) };
}

// ── Deposit Portfolio ────────────────────────────────────────────────────────

export function depositsHeadline(d: DepositPortfolioData): Headline {
	const lede =
		`${fmtMoney(d.total_deposits)} on deposit across ${d.account_count.toLocaleString()} accounts. ` +
		`${dirArrow(d.mtd_change)} ${fmtMoney(Math.abs(d.mtd_change))} this month, ` +
		`${dirArrow(d.ytd_change)} ${fmtMoney(Math.abs(d.ytd_change))} YTD.`;

	const callouts: HeadlineCallout[] = [];

	const opened = d.new_vs_closed_accounts.opened.count;
	const closed = d.new_vs_closed_accounts.closed.count;
	const netAccounts = opened - closed;
	if (netAccounts > 0) {
		callouts.push({
			tone: "success",
			label: "Growth",
			body: `Net +${netAccounts} accounts this month (${opened} opened, ${closed} closed).`,
		});
	} else if (netAccounts < 0) {
		callouts.push({
			tone: "warn",
			label: "Watch",
			body: `Net ${netAccounts} accounts (${closed} closed vs ${opened} opened).`,
		});
	}

	const totalMix = d.deposit_mix.reduce((s, x) => s + x.balance, 0);
	if (totalMix > 0) {
		const top = [...d.deposit_mix].sort((a, b) => b.balance - a.balance)[0];
		const share = (top.balance / totalMix) * 100;
		callouts.push({
			tone: share > 50 ? "warn" : "info",
			label: share > 50 ? "Concentration" : "Mix",
			body:
				share > 50
					? `${top.product} is ${fmtPct(share)} of book — single-product dominance.`
					: `Largest product: ${top.product} at ${fmtPct(share)}.`,
		});
	}

	if (d.top_25_deposits.length > 0) {
		const top = d.top_25_deposits[0];
		callouts.push({
			tone: top.share_pct > 5 ? "warn" : "info",
			label: "Top relationship",
			body: `Largest depositor holds ${fmtMoney(top.balance)} (${top.share_pct.toFixed(1)}% of total).`,
		});
	}

	return {
		lede,
		callouts: callouts.slice(0, 3),
		tone: overallTone(callouts),
	};
}

// ── Past Due ─────────────────────────────────────────────────────────────────

export function pastDueHeadline(d: PastDueData): Headline {
	const trend = d.past_due_ratio_trend;
	const lastRatio = trend.length > 0 ? trend[trend.length - 1].ratio * 100 : 0;
	const firstRatio = trend.length > 0 ? trend[0].ratio * 100 : lastRatio;
	const dirText =
		lastRatio > firstRatio + 0.1
			? "rising"
			: lastRatio < firstRatio - 0.1
				? "improving"
				: "flat";

	const lede =
		`${fmtMoney(d.past_due_total)} past due. ` +
		`Past-due ratio at ${fmtPct(lastRatio)} (${dirText} over the last ${trend.length} mo.).`;

	const callouts: HeadlineCallout[] = [];

	if (d.past_due_by_officer.length > 0) {
		const total = d.past_due_by_officer.reduce((s, o) => s + o.balance, 0);
		if (total > 0) {
			const top = [...d.past_due_by_officer].sort(
				(a, b) => b.balance - a.balance,
			)[0];
			const share = (top.balance / total) * 100;
			callouts.push(
				share > 40
					? {
							tone: "warn",
							label: "Concentration",
							body: `One officer carries ${fmtPct(share)} of past-due balance (${fmtMoney(top.balance)}).`,
						}
					: {
							tone: "info",
							label: "Spread",
							body: `Top officer holds ${fmtPct(share)} of past-due — load is reasonably distributed.`,
						},
			);
		}
	}

	if (d.delinquency_trend_13_months.length > 0) {
		const last =
			d.delinquency_trend_13_months[
				d.delinquency_trend_13_months.length - 1
			];
		const total = last.bucket_30_59 + last.bucket_60_89 + last.bucket_90_plus;
		const ninetyShare = total === 0 ? 0 : (last.bucket_90_plus / total) * 100;
		callouts.push({
			tone: ninetyShare > 35 ? "warn" : "info",
			label: "Late-stage",
			body:
				ninetyShare > 35
					? `${fmtPct(ninetyShare)} of past-due is 90+ days — late-stage delinquency dominates.`
					: `${fmtPct(ninetyShare)} of past-due is 90+ days late.`,
		});
	}

	if (d.watchlist_count_delta !== 0) {
		const dir = d.watchlist_count_delta > 0 ? "up" : "down";
		callouts.push({
			tone: d.watchlist_count_delta > 0 ? "warn" : "success",
			label: "Watchlist",
			body: `${d.watchlist_count} loans flagged for monitoring (${dir} ${Math.abs(d.watchlist_count_delta)} MoM).`,
		});
	}

	return {
		lede,
		callouts: callouts.slice(0, 3),
		tone: overallTone(callouts),
	};
}

// ── Officer / Branch ─────────────────────────────────────────────────────────

export function officerBranchHeadline(d: OfficerBranchData): Headline {
	const lede =
		`${fmtMoney(d.total_loans)} on book across ${d.account_count.toLocaleString()} loan accounts. ` +
		`Avg ticket: ${fmtMoney(d.avg_loan_balance)}.`;

	const callouts: HeadlineCallout[] = [];

	const totalMix = d.loan_mix_donut.reduce((s, x) => s + x.balance, 0);
	if (totalMix > 0) {
		const sorted = [...d.loan_mix_donut].sort((a, b) => b.balance - a.balance);
		const top = sorted[0];
		const topName = productLabel(top.product);
		const share = (top.balance / totalMix) * 100;
		callouts.push({
			tone: share > 50 ? "warn" : "info",
			label: share > 50 ? "Concentration" : "Mix",
			body:
				share > 50
					? `${topName} is ${fmtPct(share)} of the loan book — concentration risk.`
					: `Top product: ${topName} at ${fmtPct(share)} of loans.`,
		});
	}

	if (d.watchlist_trend.length >= 2) {
		const first = d.watchlist_trend[0].count;
		const last = d.watchlist_trend[d.watchlist_trend.length - 1].count;
		const delta = last - first;
		callouts.push({
			tone: delta > 0 ? "warn" : delta < 0 ? "success" : "info",
			label: "Watchlist",
			body:
				delta === 0
					? `${last} loans under watch (flat over ${d.watchlist_trend.length - 1} mo.).`
					: `${last} loans under watch (${delta > 0 ? "↑" : "↓"} ${Math.abs(delta)} over ${d.watchlist_trend.length - 1} mo.).`,
		});
	}

	if (d.top_25_borrowers.length > 0) {
		const top = d.top_25_borrowers[0];
		callouts.push({
			tone: top.share_pct > 5 ? "warn" : "info",
			label: "Top exposure",
			body: `Largest borrower: ${fmtMoney(top.balance)} (${top.share_pct.toFixed(1)}% of book).`,
		});
	}

	return {
		lede,
		callouts: callouts.slice(0, 3),
		tone: overallTone(callouts),
	};
}
