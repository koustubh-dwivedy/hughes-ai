# e-OSCAR ACDV Dispute Reason Codes: Complete Catalog, Frequency Ranking & AI-Automation Workflow Design for Credit Union Furnishers

## TL;DR
- The **current authoritative e-OSCAR code set is 32 active ACDV dispute reason codes** (per the industry's 2020 "Dispute Code and Response Code Validations" Job Aid), reorganized into 10 dispute categories; the older "~29 codes / 26 codes" figures are outdated, and several legacy codes (008, 014, 105, 107, 109, 113) have been consolidated or retired.
- Disputes are **heavily concentrated**: per Leonard Bennett's 2007 congressional testimony (reproduced in NCLC's *Automated Injustice*), five codes account for ~84% of all disputes — "not his/hers" (30.5%), status/history (21.2%), "inaccurate info/no specific dispute" (16.8%), amounts (8.8%), account closed (7.0%).
- For AI-agent design, roughly **half the code volume is fully deterministic** (field-comparison codes 15/106/114/115/116/117/118/119 → automatable end-to-end), a cluster is **semi-deterministic** (23/24/10/37/19/102/100/108 → automatable if documents/PACER data are retrievable), and a small but high-liability cluster is **discretionary** (identity fraud 103/104, not-mine 001/002/101, litigation 040, and any dispute carrying consumer images or contradictory free-text) requiring mandatory human-in-the-loop under CFPB Circular 2022-07.

## Key Findings

**1. The code set is bigger and newer than the "29 codes" folklore.** Credit-repair code sheets circulating online (TurboDispute, DisputeSuite, "Revised 4/08") list the legacy set with codes like 008, 014, 105, 107, 109. The current authoritative source — the e-OSCAR "Dispute Code and Response Code Validations Job Aid" (Revised 2/2020, marked "Confidential & Proprietary Information of Equifax, Experian, Innovis, TransUnion, and OLDE") — shows a reorganized set of 32 codes across 10 categories. One code sheet notes code 12 as a "New Dispute Code effective 06/24" and code 14 as "Obsolete Dispute Code effective 06/24," and code 105 was retired 01-20-2018 (its function split into 114 and 115).

**2. Furnisher response options are a fixed, short list.** e-OSCAR gives the furnisher exactly seven response codes: 01 (accurate as reported), 03 (delete), 04 (misrouted/reroute), 07 (delete due to fraud), 21 (updated disputed field only), 22 (updated disputed + other fields), 23 (disputed info accurate, updated unrelated fields), 24 (dispute not specific, verified ID, updated). Which response codes are even *available* is validated by e-OSCAR against the dispute code and what the furnisher enters.

**3. The 85/15 split and collections concentration define the market.** Per the CFPB's December 2012 white paper *Key Dimensions and Processes in the U.S. Credit Reporting System*, credit reporting companies "resolve an average of 15 percent of consumer disputed items internally, without getting the data furnishers involved. The remaining 85 percent are passed on to the furnishers." Approximately 40% of all disputes trace to collections items, and only 26% of ACDVs carry explanatory free-text. Product-volume context: per the same white paper, "more than half of the account information is supplied by credit card companies. Specifically, 40 percent comes from bank cards… and 18 percent comes from retail credit cards. Only 7 percent comes from mortgage lenders or servicers, and only 4 percent comes from auto lenders."

**4. Regulatory guardrails constrain automation.** CFPB Circular 2022-07 (2022) affirms that furnishers "must reasonably investigate all indirect disputes received from consumer reporting companies. These requirements remain in place even if a person does not include or use the entity's preferred format, intake forms, or documentation." The Circular names the exact evasion practices it targets: "Furnishers that require a consumer to provide additional specific documents even though the consumer has already provided the supporting documentation… [and] Consumer reporting agencies or furnishers that require a consumer to attach a completed proprietary form before investigating the consumer's dispute." CFPB Supervisory Highlights (2019, 2024) repeatedly cite furnishers that "relied heavily on automated systems that only checked their own records" — meaning a purely internal-record AI comparison is legally insufficient where external evidence (images, PACER, application docs) is available.

## Details

### DELIVERABLE 1 — COMPLETE CATALOG OF ACTIVE ACDV DISPUTE CODES

The table below is drawn verbatim from the e-OSCAR 2020 Job Aid (official/verbatim description + validation guidance), with a plain-English gloss and the tradeline fields each code implicates. Available furnisher response codes are shown as the Job Aid lists them.

| Code | Category | Verbatim description | What the consumer is actually claiming | Tradeline fields implicated | Available response codes |
|---|---|---|---|---|---|
| 001 | Ownership | Not his/hers. | "This entire account isn't mine." | Whole tradeline + identifiers (name, SSN, DOB, address) | 1, 3, 4, 6, 7, 23 |
| 002 | Ownership | Belongs to another individual with the same/similar name. | "You've mixed my file with someone with a similar name." | Whole tradeline + identifiers | 1, 3, 4, 6, 7, 23 |
| 101 | Ownership | Not liable for account (e.g., ex-spouse, business). | "It's a real account but I'm not the liable party." | ECOA/liability + identifiers | 1, 3, 4, 6, 7, 23 |
| 023 | Closed Account | Claims Account Closed. | "This account is closed." | Compliance Condition Code, Special Comment, Date Closed | 1, 3, 4, 6, 7, 21, 22, 23 |
| 024 | Closed Account | Claims Account Closed by Consumer. | "I closed this account myself." | Compliance Condition Code, Date Closed | 1, 3, 4, 6, 7, 21, 22, 23 |
| 015 | Account Specific | Credit Limit or Highest Credit/Original Loan Amount incorrect. | "The limit / high credit / original loan amount is wrong." | Credit Limit, High Credit/Original Loan Amount | 1, 3, 4, 6, 7, 21, 22, 23 |
| 100 | Account Specific | Claims account deferred. | "Payments were deferred; you shouldn't show me delinquent." | Specialized Payment Indicator, Deferred Payment Start Date | 1, 3, 4, 6, 7, 21, 22, 23 |
| 108 | Account Specific | Disputes Portfolio Type, Account Type or Terms Duration/Terms Frequency. | "The account type/terms are misclassified." | Portfolio Type, Account Type, Terms Duration, Terms Frequency | 1, 3, 4, 6, 7, 21, 22, 23 |
| 118 | Account Specific | Disputes Current Balance and/or Amount Past Due. | "The balance or past-due amount is wrong." | Current Balance, Amount Past Due | 1, 3, 4, 6, 7, 21, 22, 23 |
| 119 | Account Specific | Disputes Original Charge-off Amount, Actual Payment Amount or Scheduled Monthly Payment Amount. | "A dollar figure (charge-off/payment) is wrong." | Original Charge-off Amount, Actual Payment, Scheduled Monthly Payment | 1, 3, 4, 6, 7, 21, 22, 23 |
| 010 | Account Comments | Settlement or partial payment accepted. | "You accepted a settlement/partial payment; reflect it." | Special Comment Code | 1, 3, 4, 6, 7, 21, 22, 23 |
| 116 | Account Comments | Disputes Compliance Condition. | "The compliance condition code (e.g., dispute flag) is wrong." | Compliance Condition Code | 1, 3, 4, 6, 7, 21, 22, 23 |
| 117 | Account Comments | Disputes Special Comment Code and/or Narrative Remarks. | "A special comment/narrative remark is wrong." | Special Comment Code, Narrative Remarks | 1, 3, 4, 6, 7, 21, 22, 23 |
| 114 | Account Dates | Disputes Date Opened, Date of Last Payment and/or Date Closed. | "An account date is wrong." | Date Opened, Date of Last Payment, Date Closed | 1, 3, 4, 6, 7, 21, 22, 23 |
| 115 | Account Dates | Disputes Date of First Delinquency. | "The DOFD (which controls the 7-year clock) is wrong / re-aged." | FCRA Date of First Delinquency | 1, 3, 4, 6, 7, 21, 22, 23 |
| 039 | Account Derogatory Payments | Insurance claim delayed. | "An insurance claim delay caused the reported delinquency." | Account Status, Payment Rating, Amount Past Due, Current Balance, Account History | 1, 3, 4, 6, 7, 21, 22, 23 |
| 106 | Account Derogatory Payments | Disputes present/previous Account Status/Payment Rating/Account History. | "My status / payment rating / late-payment history is wrong." | Account Status, Payment Rating, Account (payment) History | 1, 3, 4, 6, 7, 21, 22, 23 |
| 006 | Collection | Not aware of collection. | "I never knew this was in collections." | ID + full account info | 1, 3, 4, 6, 7, 21, 22, 23 |
| 012 | Collection | Claims paid the original creditor before collection status/paid before charge off. | "I paid the original creditor before it went to collection/charge-off." | Account Status, Payment Rating, Current Balance, Amount Past Due, Account History | 1, 3, 4, 6, 7, 21, 22, 23 |
| 019 | Bankruptcy | Included in the bankruptcy of another person. | "This is someone else's bankruptcy, not mine." | Consumer Information Indicator (CII) | 1, 3, 4, 6, 7, 21, 22, 23 |
| 037 | Bankruptcy | Account included in bankruptcy. | "This account was in my bankruptcy." | Consumer Information Indicator (CII) | 1, 3, 4, 6, 7, 21, 22, 23 |
| 102 | Bankruptcy | Account reaffirmed or not included in bankruptcy. | "This was reaffirmed / not actually discharged." | CII, Account Status | 1, 3, 4, 6, 7, 21, 22, 23 |
| 103 | Fraud | Claims true identity fraud, account fraudulently opened. | "Someone opened this account in my name (identity theft)." | Whole tradeline + identifiers + fraud flags | 1, 3, 4, 6, 7, 23 |
| 104 | Fraud | Claims account take-over, fraudulent charges made on account. | "My real account was taken over / has fraudulent charges." | Special Comment Code; balances/charges | 1, 3, 4, 6, 7, 21, 22, 23 |
| 031 | Account Not Specific | Contract cancelled or rescinded. | "The underlying contract was cancelled/rescinded." | All account info | 1, 3, 4, 6, 7, 23 |
| 038 | Account Not Specific | Claims active military duty. | "I'm on active military duty (SCRA)." | All account info | 1, 3, 4, 6, 7, 21, 22, 23, 24 |
| 040 | Account Not Specific | Account Involved in Litigation. | "This account is the subject of litigation." | ID + all account info | 1, 3, 4, 6, 7, 21, 22, 23, 24 |
| 041 | Account Not Specific | Claims Victim of Natural or Declared Disaster. | "A declared disaster affected my ability to pay." | All account info | 1, 3, 4, 6, 7, 21, 22, 23, 24 |
| 110 | Account Not Specific | Claims company will change. | "The company told me it would change this." | All account info | 1, 3, 4, 6, 7, 21, 22, 23, 24 |
| 111 | Account Not Specific | Claims company will delete. | "The company told me it would delete this." | All account info | 1, 3, 4, 6, 7, 23 |
| 112 | Account Not Specific | Consumer states inaccurate information. | "Something's wrong but I didn't say what" (catch-all). | ID + all account info | 1, 3, 4, 6, 7, 21, 22, 23, 24 |
| 120 | Account Not Specific | Consumer disputes deceased ECOA. | "A deceased indicator/ECOA code is wrong (I'm not deceased / wrong person)." | ECOA Code + identifiers | 1, 3, 4, 6, 7, 21, 22, 23 |

**Retired / consolidated legacy codes (do not expect on modern ACDVs):** 008 "Late due to change of address – never received statement"; 014 "Claims paid before collection status" (obsolete eff. 06/24, folded into 012); 105 "Disputes Dates of Last Payment/Opened/First Delinquency/Billing/Closed" (retired 01-20-2018, split into 114 + 115); 107 "Disputes Special Comment/Compliance Condition Code/narrative remarks" (split into 116 + 117); 109 "Disputes current balance" (folded into 118); 113 (not present in the 2020 set). An AI ingestion layer should map any legacy code it encounters to its modern successor.

**ACDV response code list (furnisher's options), verbatim from the e-OSCAR "Responding to an ACDV" Reference Card (Effective May 2020):**
- **01 – Account information accurate as of date reported.** "The account is accurately reported and there are no changes necessary. This response cannot be used if account information has been updated on the Account Information page." (i.e., pure verify)
- **03 – Delete account.** "Remove the account from the CRAs database… no longer reported for that consumer by that CRA."
- **04 – Misrouted ACDV, please reroute.** "The dispute does not belong to the DF. Return it to the initiating CRA."
- **07 – Delete due to Fraud.** Delete because of fraud.
- **21 – Updated disputed account information only.** Data entered in the disputed field(s).
- **22 – Updated disputed account information. Additional account information was also updated.**
- **23 – Disputed information accurate. Updated account information unrelated to the dispute.**
- **24 – Consumer's dispute not specific. Consumer Information verified. Account information updated.**

**Verification indicators (identity/ownership disputes):** Same / Different / Unknown, comparing the furnisher's record to the CRA-reported data.

**Key Metro 2 Compliance Condition Codes (CCC) the agent must set/clear:** XB (account information disputed by consumer under FCRA — set while investigation pending); XC (completed investigation of FCRA dispute – consumer disagrees); XH (account previously in dispute – now resolved, reported by furnisher); XR (removes the most recently reported CCC); plus XA/XD/XE (closed at consumer request combinations) and XF/XG/XJ (FCBA). Bankruptcy status is carried in the Consumer Information Indicator (CII), not the account status; discharged accounts must be reported with $0 balance and appropriate "included in bankruptcy" coding.

### DELIVERABLE 2 — FREQUENCY / OCCURRENCE RANKING

The only code-level frequency dataset in the public record traces to **Leonard A. Bennett's June 19, 2007 testimony** to the House Financial Services Committee ("Credit Reports: Consumers' Ability to Dispute and Change Inaccurate Information"), reproduced in the **National Consumer Law Center's 2009 report *Automated Injustice*** (Chi Chi Wu, with Bennett and Evan Hendricks). The frequently repeated "the same four codes were used over 90% of the time" is a secondary-source popularization; NCLC's own framing (Chi Chi Wu, 2021 House Financial Services testimony) states the credit bureaus "used the same four or five codes over 80% of the time," and the underlying primary figure is **five codes = 84.3%**. The precise table:

| Rank | Dispute (Bennett/NCLC description) | Modern code equivalent | Share of disputes | Confidence |
|---|---|---|---|---|
| 1 | Not his/hers | 001 | 30.5% | High (primary testimony) |
| 2 | Disputes present/previous Account Status/History | 106 | 21.2% | High |
| 3 | Claims Inaccurate Information (no specific dispute) | 112 | 16.8% | High |
| 4 | Disputes amounts | 118 (balance) / 119 | 8.8% | High |
| 5 | Claims account closed by consumer | 024 (023) | 7.0% | High |
| — | **Top 5 subtotal** | | **84.3%** | High |
| 6–32 | All remaining codes (fraud 103/104, bankruptcy 019/037/102, dates 114/115, limit 015, military 038, disaster 041, litigation 040, etc.) | | ~15.7% combined | Medium |

**Best-estimate frequency bands for product design (blending 2007 code data with CFPB 2012/2021 category data; flagged as estimates where noted):**

| Band | Codes | Est. share | Basis |
|---|---|---|---|
| **Tier 1 – dominant** | 001, 106, 112 | ~65–70% | Bennett 2007 (measured) |
| **Tier 2 – common** | 118/119 (amounts), 023/024 (closed), 015 | ~15–20% | Bennett 2007 + inference |
| **Tier 3 – moderate** | 103/104 (fraud), 037/019/102 (bankruptcy), 114/115 (dates), 006/012 (collection), 116/117 (comments) | ~10–12% | Inference from CFPB collections/fraud data |
| **Tier 4 – rare/edge** | 031, 038, 039, 040, 041, 100, 108, 110, 111, 120 | <3% combined | Inference; these are niche |

**Category-level (measured, CFPB Dec 2012):** ~40% of all NCRA disputes link to **collections items**; collections trade lines have the highest dispute rate (~1.1%/yr). Because credit cards supply more than half of all tradelines (40% bank card + 18% retail card), the absolute volume of card-related status/balance disputes (106/118) is large even though per-account dispute rates are lower.

**Portfolio-mix shifts (CFPB "Disputes on Consumer Credit Reports," Nov 2021):** dispute *outcomes* differ sharply by product. For **auto loans**, "more than 40 percent of auto loan accounts with dispute flags clos[e] with the dispute flag still present within four years… about 17 percent of disputed auto loans were closed at the time of the initial dispute flag and an additional four percent were closed within the first quarter." For **student loans**, "apparent deletions were about 30 percent more common for student loans with dispute flags than student loans without dispute flags" — a gap largely reflecting inconsistent/consolidated-loan reporting rather than dispute resolution per se. **General-purpose credit cards** more often have the dispute flag removed with the account staying open; **retail cards** are more likely to be closed or deleted than general cards. Implication for a credit union: **auto and collections portfolios skew toward status/balance/date disputes (106/118/114/115) and closure outcomes**, while card portfolios skew toward status/balance disputes with verify/modify outcomes.

**Credit Repair Organization (CRO) impact on the mix:** CROs disproportionately trigger **001/002 "not mine"** (described by consumer attorneys as "the easiest dispute to make" — broad, non-specific) and **103 identity-fraud** templates, plus **112 "inaccurate information"** shotgun disputes. Regulation V (12 CFR 1022.43) lets a furnisher treat a *direct* dispute as frivolous if it "has a reasonable belief that the direct dispute is… submitted on a form supplied to the consumer by[] a credit repair organization" — but this frivolous exception does NOT apply to indirect (ACDV) disputes routed through a CRA, which must still be investigated. AI systems should flag likely-CRO template patterns for tracking but must not auto-reject indirect disputes on that basis.

### DELIVERABLE 3 — GRANULAR RESOLUTION WORKFLOW PER CODE CLUSTER

For each cluster: Systems Touched → Decision Logic → Deterministic classification → AI autonomy recommendation → SLA/timing → letters/special workflows. Systems are mapped to a Fiserv DNA credit union (Seattle Credit Union runs the DNA core, per Fiserv/Credit Union Times reporting).

---

#### CLUSTER A — Field-comparison / "data accuracy" codes: 015, 106, 118, 119, 114, 115, 116, 117, 108, 039
**(The automation core — highest volume, most deterministic.)**

- **Systems touched:** Fiserv DNA core (account master, status, balance, payment history, dates, credit limit); the credit union's **Metro 2 reporting engine / credit reporting work file** (to see what was actually last furnished); e-OSCAR itself for the ACDV response and carbon copies. For 039 (insurance delay), also the insurance-claim note or collateral-protection/GAP record.
- **Decision logic:** Compare the specific disputed field in the ACDV "Original" column against the DNA system-of-record value as of the "Date of Account Information." Three outcomes: (a) **match → verify** (Response 01, or 23 if unrelated fields also need refresh); (b) **mismatch, SOR is correct → modify** (enter corrected value in the Response field → Response 21, or 22 if additional fields updated); (c) rarely, field can't be substantiated → consider delete of the field/tradeline. For 115 (DOFD), enforce the anti-re-aging rule: the DOFD must be the original date of first delinquency that led to the current status and must never be advanced.
- **Deterministic classification: FULLY DETERMINISTIC.** These are pure field comparisons against DNA. This is where the product earns its keep.
- **AI autonomy recommendation:** **Autonomous end-to-end** for verify-or-modify where (i) the DNA field is populated and internally consistent (no Metro 2 contradictions such as "open + charge-off"), (ii) no consumer image is attached, and (iii) the free-text field does not contradict the code. The agent writes the corrected value back and selects Response 21/22/01/23. **Draft-for-human-approval** when the field is blank/ambiguous in DNA, when correcting would flip a derogatory to positive (or vice versa), or when the correction reveals a systemic coding error (CFPB requires root-cause analysis).
- **SLA/timing:** Bureau sets a Response Due Date in the ACDV header (typically leaving the furnisher ~14–21 days inside the FCRA 30-day / 45-day-with-new-info window). On expiration, the CRA deletes or modifies per the consumer's version — so these must clear well before due date.
- **Letters/CCC:** No consumer letter required for indirect (ACDV) disputes — the CRA notifies the consumer. Set XB while pending; on completion move to XH (or XR to remove) per Metro 2. For *direct* disputes of these fields, the furnisher must send the consumer the investigation result.

---

#### CLUSTER B — Closed / settlement / deferred: 023, 024, 010, 100
**(Semi-deterministic — deterministic once a status/date/comment is confirmed.)**

- **Systems touched:** DNA core (account status, date closed, deferred-payment indicators); collections system notes (for settlement terms on 010); document imaging (settlement letters); Metro 2 engine; e-OSCAR.
- **Decision logic:** For 023/024, verify Date Closed, Compliance Condition Code, and (024) that closure was consumer-initiated. For 010, verify the Special Comment Code reflects settlement/partial payment (e.g., "Settled – less than full balance" / "Paying under partial payment agreement"). For 100, verify Specialized Payment Indicator + Deferred Payment Start Date.
- **Deterministic classification: SEMI-DETERMINISTIC.** Fully automatable IF the closure date/settlement comment/deferral record is retrievable and matches; otherwise route to human.
- **AI autonomy recommendation:** **Autonomous** when DNA cleanly shows the closure/settlement/deferral consistent with the claim. **Draft-for-approval** when a settlement (010) requires reading a settlement agreement image, or when closing would zero a balance the SOR still shows outstanding.
- **SLA/letters:** Same ACDV timing. Set/clear CCC (XA/XR family for closures).

---

#### CLUSTER C — Bankruptcy: 037, 019, 102
**(Semi-deterministic with external verification.)**

- **Systems touched:** DNA core; **bankruptcy tracking feed (PACER / AACER)**; document imaging (discharge order, reaffirmation agreement); Metro 2 engine (Consumer Information Indicator field); e-OSCAR.
- **Decision logic:** Bankruptcy is reported via the **CII**, not account status. For 037 (included in bankruptcy), verify the CII and that a discharged account shows **$0 balance, $0 past due, no post-petition lates**, and appropriate "included in bankruptcy" coding. For 019 (someone else's bankruptcy), verify the CII belongs to the correct consumer (mixed-file check). For 102 (reaffirmed / not included), verify reaffirmation → report **open and current**, not discharged. The automatic stay (pre-discharge) and discharge injunction (post-discharge) both prohibit continued derogatory reporting.
- **Deterministic classification: SEMI-DETERMINISTIC** (deterministic if PACER/AACER confirms chapter, filing date, discharge date, and reaffirmation status).
- **AI autonomy recommendation:** **Autonomous** to set CII + $0 balance when PACER/AACER confirms discharge and DNA agrees. **Mandatory human review** where reaffirmation is claimed (102) but not documented, where a mixed-file bankruptcy (019) is alleged, or where the discharge would require deleting derogatory history — because CFPB Supervisory Highlights specifically flagged bankruptcy mis-coding.
- **SLA/special workflow:** ACDV timing. If a stay-violation or discharge-injunction issue surfaces, escalate to counsel (contempt/sanctions risk).

---

#### CLUSTER D — Identity fraud & takeover: 103, 104 (plus 605B blocks)
**(Discretionary — mandatory human-in-the-loop.)**

- **Systems touched:** DNA core; **loan origination system + application documents / e-signatures** (to test whether the application is genuine); **fraud case management** system; document imaging (FTC Identity Theft Report, police report, ID); e-OSCAR (ACDV + **Block Notifications** under FCRA §605B).
- **Decision logic:** For 103 (true identity fraud), the question is whether the account was fraudulently opened — compare application identity data, IP/device, signatures, and any consumer affidavit. Correct outcome for confirmed fraud is **Response 07 (Delete due to Fraud)**. For 104 (takeover / fraudulent charges), the underlying account is the consumer's — remove fraudulent charges/adjust balance and set the appropriate special comment. Separately, under **FCRA §605B (15 U.S.C. §1681c-2)**, when a consumer files an identity-theft report, the CRA must block within **4 business days** and "promptly notify the furnisher" that the information may be identity theft, that a block was requested, and the effective dates; the furnisher then **may not refurnish** blocked information unless it later learns the info is correct, and **may not sell/transfer/place for collection** a debt identified as identity theft.
- **Deterministic classification: DISCRETIONARY / JUDGMENT-HEAVY.**
- **AI autonomy recommendation:** Agent may **assemble the evidence package** (pull application docs, compare signatures, retrieve the ID-theft report image, draft a recommended Response 07 + block acknowledgment) but a **human must approve any deletion/fraud determination**. Fraud deletions are irreversible reputationally and are a litigation and regulatory hotspot. Never auto-verify a fraud claim against internal records only (the exact failure pattern CFPB cited).
- **SLA/letters:** ACDV due date applies; 605B blocks run on the separate 4-business-day CRA clock. Fraud outcomes commonly generate consumer-facing confirmation for direct disputes.

---

#### CLUSTER E — Ownership / liability: 001, 002, 101
**(Discretionary when evidence conflicts; semi-deterministic when clean.)**

- **Systems touched:** DNA core (identity match); loan origination system + signed application/e-signatures; document imaging; e-OSCAR (verification indicators Same/Diff/Unknown).
- **Decision logic:** Compare full identifiers (name, SSN, DOB, address) and account ownership against DNA and the signed application. For 001/002 the test is whether this consumer is the account holder (or a mixed file); for 101 whether this consumer is a liable party vs. authorized user/ex-spouse/business. Outcomes: verify with confirmed ID (Response 01/23), or delete (Response 03) if not the consumer's.
- **Deterministic classification: SEMI-DETERMINISTIC → DISCRETIONARY.** Clean SSN/DOB/name match with a signed application = automatable verify. Any conflict (partial SSN match, similar-name family member, consumer affidavit or image asserting non-ownership) = human review, because "not mine" is the single most-abused CRO template and the most litigated category.
- **AI autonomy recommendation:** **Autonomous verify** only on a strong multi-factor identity match with an on-file signed application and no attached consumer image/affidavit. Otherwise **draft for human review**; escalate all conflicting-evidence and mixed-file cases.
- **SLA/letters:** ACDV timing; deletions send carbon copies to all CRAs the furnisher reports to.

---

#### CLUSTER F — Military (SCRA): 038
- **Systems touched:** DNA core; **SCRA / DMDC (Defense Manpower Data Center) military verification database**; document imaging (orders); Metro 2 (Special Comment "AI – Recalled to active military duty"); e-OSCAR.
- **Decision logic:** Verify active-duty status via DMDC and apply SCRA protections (6% interest cap on pre-service debt; a lender "can't send negative information to a credit reporting company because you are using your SCRA rights"). Note: SCRA does not itself forgive lawful late reporting — but a furnisher cannot report negative info because the member invoked SCRA rights.
- **Classification: SEMI-DETERMINISTIC** (DMDC lookup is a clean external check).
- **AI autonomy:** **Autonomous** to run the DMDC check and apply the rate/status flag; **draft for approval** where SCRA eligibility depends on "materially affected" judgments.
- **Note:** Available response codes for 038 include 24, reflecting non-specific military claims.

---

#### CLUSTER G — Collection: 006, 012
- **Systems touched:** collections system + notes; DNA core; document imaging (proof of pre-charge-off payment); e-OSCAR. Verify ID + account status, payment rating, balance, past-due, history.
- **Classification: SEMI-DETERMINISTIC.** Automatable when payment records substantiate; human review when the consumer alleges payment to the *original creditor* (012) that the collection agency can't see — CFPB flagged debt-collector furnishers that failed to consult client/creditor records.
- **AI autonomy:** **Draft for approval** on 012 where cross-entity records are needed; autonomous on 006 where ID + collection placement are cleanly documented.

---

#### CLUSTER H — Litigation, disaster, contract, "company will change/delete," catch-all, deceased: 040, 041, 031, 110, 111, 112, 120
- **040 Litigation:** DISCRETIONARY — **escalate to legal/counsel, apply litigation hold.** Never auto-respond.
- **041 Disaster:** SEMI-DETERMINISTIC — apply disaster special comment (e.g., "AW – Affected by natural or declared disaster"); autonomous where a declared-disaster flag is confirmed.
- **031 Contract cancelled/rescinded:** DISCRETIONARY — requires reading contract docs; draft for human.
- **110/111 "company will change/delete":** DISCRETIONARY — verify whether any such promise exists in notes; these are frequently CRO-driven; human review recommended.
- **112 "inaccurate information" (catch-all, ~17% of volume):** Because the consumer gave no specific field, the agent must verify ALL account information; treat as **draft-for-approval by default**, using Response 24 ("dispute not specific") only after a full-record verification. This code is a top-3 volume driver, so a strong 112 workflow materially affects automation rate.
- **120 Deceased ECOA:** SEMI-DETERMINISTIC — verify ECOA/deceased indicator and identifiers (often a mixed-file or wrong-person issue); autonomous to correct an erroneous deceased flag on a clean identity match.

---

### Cross-cutting mechanics

- **Images/attachments:** CRAs "may provide images of relevant documentation a consumer provides." The furnisher "is required to take at least one" action (View/Print/Download) on each image. File types: TIF/TIFF (most common), JPG, GIF, PNG. **Any ACDV carrying an image should force human-in-the-loop review** (or at minimum AI image-extraction + human confirmation), because CFPB Circular 2022-07 forbids ignoring consumer-submitted documentation. Historically images flowed poorly (the 2012 CFPB paper noted mailed-dispute documents generally were not forwarded); e-OSCAR added image capability after CFPB pressure, but image presence remains the single strongest human-review trigger.
- **FCRA Relevant Information free-text field:** present in only ~26% of ACDVs (CFPB 2012); the furnisher is instructed to "Review the Dispute Code(s) and the FCRA Relevant Information… to determine why the consumer has disputed." When the free-text **contradicts or expands** the numeric code (e.g., code 106 but text says "paid in full, balance should be zero, account closed" — as in *Powers v. SELCO CU*), the furnisher cannot limit its investigation to the literal code; courts have held a narrow code-only response can be unreasonable. **AI rule: if free-text semantically conflicts with the dispute code, escalate to human.**
- **Outcome-rate signal for automation expectations:** CFPB Supervisory Highlights repeatedly warn against two failure modes — (1) auto-**verifying** using internal records only, and (2) auto-**deleting** tradelines on receipt of a dispute without investigation (specifically cited for debt collectors). Both extremes are violations. The AI must land in the middle: investigate, then verify OR modify OR delete on evidence.

## Recommendations

**Stage 1 (MVP — ship the deterministic core):** Automate end-to-end only Cluster A field-comparison codes (015, 106, 118, 119, 114, 115, 116, 117, 108, 039) plus clean-match Cluster B (023/024/010/100). These map to ~40–55% of total ACDV volume (106 + amounts + closed ≈ 37% alone from Bennett data, before adding 015/114/115). Gate every autonomous action on three conditions: (i) no image attached, (ii) free-text does not contradict the code, (iii) DNA field is populated and Metro 2-consistent. Everything else drafts for a human.

**Stage 2 (add semi-deterministic with external connectors):** Integrate PACER/AACER (bankruptcy 019/037/102), DMDC (military 038), and collections/LOS document retrieval (006/012, 023-settlement). Move these to "autonomous when the external check confirms, draft otherwise."

**Stage 3 (assistive-only for discretionary):** For fraud (103/104), ownership-with-conflict (001/002/101), litigation (040), contract (031), and any image-bearing or contradictory-free-text ACDV, build an evidence-assembly + draft-response copilot that always requires human sign-off. Never let the model auto-delete for fraud or auto-verify "not mine."

**Benchmarks that should change the automation posture:**
- If measured auto-handling accuracy on Cluster A exceeds ~99% against human QA over a statistically meaningful sample, expand autonomous scope to clean-match Cluster E verifies.
- If the credit union's dispute mix shows >40% code 112 (catch-all), invest in a "full-record verification" routine before promising high automation rates — 112 caps how much can be safely automated.
- If CFPB issues its long-signaled FCRA rulemaking (data-broker / medical-debt / dispute-investigation rules), re-audit the deterministic gates, especially around consumer documentation.
- Track your delete rate by code: a spike in Response 03/07 is exactly the metric CRAs use to flag "unreliable furnishers" (CFPB 2024) — keep deletions evidence-backed.

**For the Seattle Credit Union demo:** Lead with the DNA-to-e-OSCAR round trip for Cluster A (their Support Services team's daily bread), show the three human-in-the-loop gates (image / free-text conflict / blank field), and explicitly name Circular 2022-07 and the 2024 Supervisory Highlights "internal-records-only" finding as the reason your product drafts rather than auto-verifies the hard cases. That framing signals compliance credibility to a Loan Servicing audience.

### Summary matrix for product design

| Code(s) | Freq band | Automation class | Systems touched | Human-in-the-loop trigger |
|---|---|---|---|---|
| 106, 118, 119, 015, 114, 115, 116, 117, 108 | Tier 1–2 | **Autonomous (deterministic)** | DNA, Metro 2 engine, e-OSCAR | Image attached; free-text conflict; blank/inconsistent field |
| 039 | Tier 4 | Autonomous (deterministic) | DNA, insurance note, Metro 2 | Insurance claim unverifiable |
| 023, 024, 010, 100 | Tier 2–3 | **Semi-deterministic** | DNA, collections notes, imaging | Settlement image; balance conflict |
| 037, 019, 102 | Tier 3 | Semi-deterministic | DNA, PACER/AACER, imaging, CII | Reaffirmation undocumented; mixed-file; derogatory deletion |
| 038 | Tier 4 | Semi-deterministic | DNA, DMDC, imaging | "Materially affected" judgment |
| 006, 012 | Tier 3 | Semi-deterministic | Collections, DNA, imaging | Payment-to-original-creditor (012) needs cross-entity records |
| 041, 120 | Tier 4 | Semi-deterministic | DNA, disaster flag / ECOA | Disaster undeclared; identity conflict |
| 001, 002, 101 | Tier 1 (001) / Tier 4 | **Discretionary** (auto only on clean match) | DNA, LOS/application, imaging | Any identity conflict, affidavit, image, family similar-name |
| 103, 104 | Tier 3 | **Discretionary (mandatory review)** | DNA, LOS, fraud case mgmt, 605B block, imaging | Always — no auto fraud delete/verify |
| 040 | Tier 4 | **Discretionary (escalate to counsel)** | DNA, legal hold | Always |
| 031, 110, 111 | Tier 4 | Discretionary | DNA, contract docs, notes | Always (read docs / verify promise) |
| 112 | Tier 1 | Discretionary (draft-by-default) | DNA (all fields), imaging | Non-specific → full-record verify + human |

## Caveats
- **Code-count and definitions:** The 32-code catalog and all verbatim definitions/response-code availability come from the e-OSCAR 2020 "Dispute Code and Response Code Validations Job Aid" and the May 2020 "Responding to an ACDV" Reference Card. e-OSCAR is a private, proprietary system (owned by Online Data Exchange LLC); the master "Consolidated Code Sheet" is behind licensing, so minor post-2020 additions/retirements (e.g., the 06/24 code 12/14 change) may not be fully reflected. Verify against the current e-OSCAR Training Hub before shipping.
- **Frequency data is old and imperfect:** The only code-level percentages (Bennett 2007 / NCLC 2009) are ~17 years old, predate the 105→114/115 and 107→116/117 reorganizations, and were presented in litigation/advocacy context. The "four codes / 90%" claim is an imprecise popularization; NCLC's own later framing is "four or five codes over 80% of the time," and the defensible primary figure is five codes = 84.3%. Tier bands beyond the top five are informed estimates, not measured per-code data — the CFPB 2012 and 2021 reports give category/product-level, not reason-code-level, distributions. Treat all Tier 3–4 shares as directional.
- **Systems mapping is inferential:** Seattle Credit Union's use of Fiserv DNA core is confirmed publicly, but the specific LOS, imaging, collections, and fraud-case systems, and whether they use e-OSCAR's API vs. web UI, are assumptions — confirm in discovery.
- **Regulatory flux:** CFPB enforcement posture and rulemaking are actively shifting (e.g., the January 2025 Experian suit; 2024 Supervisory Highlights). Circular 2022-07's "reasonable investigation" standard is the binding constraint on automation and should be treated as a hard design boundary, not a nice-to-have.
- One low-quality secondary source ("Dispute Beast") referenced a "2026 FCRA update" and a rule that DOFD cannot be changed after disputes; the DOFD/re-aging prohibition is well-grounded in existing FCRA §605/§623 and Metro 2, but treat any specific "2026 FCRA update" claim as unverified marketing until confirmed against primary regulatory text.