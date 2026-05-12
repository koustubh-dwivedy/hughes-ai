# Eval Quality Audit — 2026-05-10

## Scope
For each of the 24 must-pass questions in
`packages/nl-engine/benchmarks/questions.yaml`: read the question text,
read the ground-truth rows, decide if the question has a single
defensible interpretation and whether GT matches that interpretation.
Audit performed independently of the catalog audit
(`docs/audits/2026-05-10-catalog-quality.md`) and of any agent
behavior — purely about question/GT correctness.

## Decision rule (from plan)

- GT correction matches the natural reading of the question → fix the YAML.
- Wording is genuinely ambiguous → tighten the wording, don't hard-code
  one reading in GT.
- Agent behavior is wrong (e.g. returns extra columns) → leave wording
  + GT alone; Step 1 (docstring restore) is what fixes it.
- **We don't lower the bar by making the eval easier.**

## Findings

### Q23 — initially flagged in the forensic, on review NOT a bug

**Question**: "Show loan lifecycle event counts (new / renewed /
paid_off) for the latest month."
**Ground truth**: `[{event_type: "new", lifecycle_event_count: 7}]`

The forensic suggested rewriting the GT to "expect 3 rows broken out by
event_type." Verified against actual data:

```sql
SELECT event_type, SUM(loan_count)
FROM fct_loan_lifecycle_events
WHERE as_of_month = '2026-04-01'
GROUP BY event_type;
-- ('new', 7)
```

The latest month genuinely has only one event_type (`'new'`) — there
are no `'paid_off'` or `'renewed'` events that month. The 1-row GT is
factually correct. The parenthetical `(new / renewed / paid_off)` in
the question text gives the LLM a rough sense of what event types
exist in the schema; it is not a directive to return three rows. The
question reads "show event counts for the latest month" — which is
answered by 1 row when only one event_type is present.

**Verdict**: leave the question and GT unchanged. If the agent fails
this question, it is because of how it shapes its answer (extra
columns, different aggregation), which Step 1's docstring restore
addresses.

### Q8 — initially flagged in the forensic, on review NOT a bug

**Question**: "What's our month-to-date deposit change for the latest
month?"
**Ground truth**: `[{mtd_deposit_change: -1197182.95}]`

The forensic suggested the wording is ambiguous on grain (blended vs
by-category). Re-reading: the question asks for "our MTD deposit
change" — a single aggregate for the credit union, not a breakdown.
The GT (one row, one number) matches that reading. Splitting by
category would be a different question. The wording is unambiguous.

**Verdict**: leave the question and GT unchanged.

### Other 22 must-pass questions

Spot-checked: ground-truth rows match the natural reading of each
question. No question wordings ask for one shape while their GT
provides another. No question is rendered unanswerable by the catalog
(post Step 3 catalog fix; see Step 4 Pass 4b coverage matrix).

## Conclusion

Zero eval-quality bug fixes warranted from this audit. The forensic's
preliminary read of Q23/Q8 was overruled by checking the underlying
data: in both cases the GT is correct and the wording is defensible.

The eval set is clean. Where the agent fails, the failure is in the
agent (Step 1 docstring restore) or the catalog (Step 3 F-001 fix), not
in the eval.
