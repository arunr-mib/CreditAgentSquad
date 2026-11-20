# Innovation-banking book and lending layer: design

Date: 2026-11-20. Status: **draft for owner review**. It extends `2026-11-17-credit-agent-squad-design.md` (the owner's source of truth) and does not change it; where this draft needs a change there, section 13 proposes it.

## 1. Purpose and scope

Move Credit Agent Squad from a quarterly commercial-and-industrial (C&I) book to a book that is about 80% venture-backed innovation-banking clients and 20% traditional, and give the engine the lending layer those clients need: monthly reporting, SaaS spreading lines, runway and minimum-cash covenants, funding events and the signals that matter for startups.

What stays: the core that makes figures trustworthy. Agents reason, code calculates, guardrails verify, people decide; the model never types a number; every figure is a stored fact with provenance; scope injected by code; append-only hash-chained ledger; two-person approval; abstain over guess. None of these change.

Out of scope here: the user experience (its own spec, `2026-11-20-squad-experience-design.md`), real connectors, a client portal, email-in intake.

## 2. The book

20 borrowers: 16 innovation-banking clients and 4 traditional C&I clients. The bank stays "Bank of Stoic"; every document carries `SYNTHETIC - FOR DEMONSTRATION`. All names are invented; before anything is shown outside the team, each name is checked against real companies and changed if it collides.

### 2.1 Innovation clients (16)

The 12 from the demo keep the demo's figures at 31 October 2026 (unrestricted cash, average monthly net burn over the last three months, RML = cash ÷ burn):

| Client | Sector · stage | Cash | Burn / mo | RML | Situation |
|---|---|---|---|---|---|
| Dataflake Inc | Data infrastructure · Series A | $4.6M | $0.65M | 7.1 | Minimum-cash miss hidden by pledged cash on the certificate; $8M Series B extension, term sheet closing 12 December |
| Lumora Health | Digital health · Series B | $4.0M | $0.42M | 9.5 | October reporting 12 days late |
| Brightvane Energy | Climate hardware · Series A | $5.5M | $0.45M | 12.2 | Runway falling toward the watch level |
| Mosswell Robotics | Robotics · Series A | $7.8M | $0.60M | 13.0 | Clean |
| Halcyon Grid | Energy software · Seed+ | $2.6M | $0.20M | 13.0 | Series A expected Q1 (funding event tracked) |
| Quillon AI | Applied AI · Series B | $12.0M | $0.80M | 15.0 | Clean |
| Kelvra Bio | Biotech tools · Series B | $9.2M | $0.50M | 18.4 | Milestone tranche in February |
| Orbitline Systems | Space software · Series A | $3.9M | $0.21M | 18.6 | Clean |
| Stripple Tech | Fintech infrastructure · Series B | $6.6M | $0.30M | 22.0 | October package: new line (contract liabilities), misread capitalised software, unplaceable MRR file |
| Veridia Payments | Payments · Series C | $14.0M | $0.55M | 25.5 | Clean |
| Tessaract Labs | Developer tools · Series B | $11.0M | $0.40M | 27.5 | Clean |
| Pellucid Sensors | Industrial IoT · Series A | $6.3M | $0.22M | 28.6 | Clean |

Four more, each carrying a situation the demo does not show:

| Client (working name) | Sector | Situation |
|---|---|---|
| Corvane Analytics | B2B SaaS · Series B | Revenue (ARR) below the approved plan floor two months running |
| Nimbusfield Security | Cybersecurity · Series A | Funding round slipped past the date the bank was told; runway under 9 months |
| Tidewell Medical | Medical devices · Series B | Bank statements and the certificate disagree on cash; one account newly restricted |
| Ferrogate Cloud | Cloud infrastructure · Series C | Cash-flow positive this quarter (net burn ≤ 0): RML is "not meaningful", not a divide-by-zero |

### 2.2 Traditional clients kept from v1 (4)

`kestrel-bay-packaging`, `harrowgate-precision`, `briarstone-beverage` (these three carry live recordings) and `pellham-grain` (reported breach). They keep their quarterly cadence, template `ci-1`, terms and signed answer-key rows unchanged, so their recordings and measured accuracy carry over.

### 2.3 The v1 book stays as a fixture

The 21-borrower v1 generator is kept, frozen, as the **legacy C&I book** that existing engine tests run on. The new book sits beside it (`synthetic/books/innovation/`). Nothing proven on v1 is lost.

## 3. Reporting cadence and dates

- As-of: a Thursday in mid-November 2026; current period 31 October 2026 for innovation clients; 30 September 2026 for the C&I four.
- Innovation clients report monthly: management financials within 30 days of month end, compliance certificate monthly, MRR/ARR report monthly, bank statements monthly, audited annual statements within 180 days of year end.
- History: 18 monthly periods (May 2025 to October 2026) of truth per innovation client, so three-month averages and year-on-year comparisons exist.
- Cycles open per frequency: one monthly cycle per innovation client per month; quarterly for C&I.

## 4. Spreading template `vc-1`

A second template beside `ci-1`; each borrower record names its template. Lines (all monthly; flows also carry year-to-date and trailing-three-months bases):

- **Income statement:** subscription revenue, services revenue, total revenue, cost of revenue, gross profit, R&D, sales and marketing, G&A, stock-based compensation (memo), operating loss, interest, other income, net loss.
- **Balance sheet:** cash in operating accounts, cash pledged or restricted, short-term investments, accounts receivable, prepaid and other, capitalised software (net), other intangibles, other assets; accounts payable, accrued expenses, deferred revenue / contract liabilities (current and long-term), venture debt (current and long-term), convertible notes, SAFEs, other liabilities, preferred equity, common equity.
- **Cash flow (direct or indirect, as reported):** operating cash flow, capex, capitalised software spend, financing inflows (equity, debt), net change in cash.
- **SaaS metrics (from the MRR/ARR report, each a stored fact with its page):** MRR, ARR, net new ARR, customers, net revenue retention where reported.

A line not in the template is an error, as today. Mapping a new line (Stripple's "contract liabilities") is a question to the analyst, never a guess.

## 5. Covenants

New archetypes, each compiled to the existing expression engine and tested against the truth model:

| Archetype | Definition | Notes |
|---|---|---|
| `min_unrestricted_cash` | Cash in deposit accounts under the bank's control, excluding pledged, escrowed or restricted cash, at the test date ≥ threshold | The definition clause is quoted from the agreement; restricted accounts come from bank statements |
| `min_runway_months` | RML = unrestricted cash ÷ average monthly net burn over the last three months ≥ threshold | Net burn = −(operating cash flow + capex + capitalised software spend); financing inflows excluded. If average net burn ≤ 0, the result is "not meaningful: cash-flow positive" and the test is compliant with that note; never a division by zero or by a negative |
| `revenue_vs_plan` | Trailing-three-months revenue (or ARR, per terms) ≥ X% of the approved plan for the same months | Plan figures are approved terms data entered by a person and versioned like other terms, never read from a budget column in a borrower document |
| Reporting covenants | Each document type due by its day; late is a finding, not a breach decision | Exists today; monthly due dates added |

New period basis `avg_last_3m` in `calc/expr.py`. Existing C&I archetypes are unchanged.

## 6. Funding events

A funding event is a first-class record per borrower: type (equity round, extension, milestone tranche, venture debt), amount, expected close, status (expected, signed, closed, slipped), and evidence documents (term sheet, closing notice). Waiver conditions can reference an event ("the $8M arrives by 15 December"); the engine checks the condition against the event's status and evidence, and raises a work item if the date passes unmet.

## 7. Signals

| Signal | Fires when | Severity |
|---|---|---|
| `runway_below_watch` | RML under 12 months | high under 9, otherwise medium |
| `runway_falling` | RML down three months running | medium |
| `burn_rising` | three-month average burn up more than 20% on the prior three months | medium |
| `funding_slipped` | a funding event passes its expected close without closing | high |
| `revenue_below_plan` | trailing three months under plan, before it breaches | medium |
| `reporting_late` | exists today | as today |

`net_loss` does not apply to the `vc-1` template. C&I rules are unchanged for C&I borrowers.

## 8. Documents and intake

New document types: monthly management financials, MRR/ARR report, bank statement, monthly compliance certificate, term sheet, investor update. Intake recognises monthly period phrases ("month ended", "one month ended", "ten months ended"); the quote guardrail's period phrases gain the same. A file that names no company or shows a different period is held with one question (the demo's MRR file).

## 9. Teach once

When an analyst confirms a mapping or corrects a figure and ticks "Remember", a lesson is written to `analyst_lessons` (borrower, topic, the person's own words, link to the decision). Agents already read lessons; the next cycle uses it and says so ("page 3 again, as you showed me last month"). Only a person's written reasoning becomes a lesson.

## 10. Scenarios (what each must make the engine do)

| Scenario | Client | Engine must | Expected exception |
|---|---|---|---|
| Pledged cash counted | Dataflake | Exclude restricted cash; quote §1.1; flag the certificate mismatch | Covenant breach reported compliant |
| Late monthly package | Lumora | Mark overdue; draft a reminder for the analyst | Reporting late |
| Unplaceable file | Stripple | Hold `mrr_export.xlsx` (no company, wrong year) with one question | Document held |
| New line | Stripple | Ask where "contract liabilities" maps | Spread question |
| Spend read as balance | Stripple | Doubt capitalised software when intangibles do not tie | Figure flagged |
| Runway falling | Brightvane | Fire `runway_falling` | Signal |
| Plan miss | Corvane | Test revenue against approved plan | Covenant breach |
| Funding slipped | Nimbusfield | Fire `funding_slipped`; runway under 9 | Signal and work item |
| Restricted account | Tidewell | Reconcile statements to certificate | Cash mismatch |
| Cash-flow positive | Ferrogate | RML "not meaningful"; no division | None (compliant, noted) |
| C&I traps | kept four | As in v1 | As in v1 |

## 11. Evals

- The generator computes expected values independently of `app/calc` (unchanged rule); a cross-check test runs both books.
- New answer-key rows for the 16 innovation clients arrive unsigned; the owner signs them before any live or record run. Rows for the kept four stay signed.
- Stand-in reader for the new document types; the stand-in suite must agree with the truth in full on both books.
- Gate unchanged: fail on any invented number or false compliant.
- Recordings for the kept three replay; new recordings come from one live record pass, asked first with a cost estimate labelled as an estimate.

## 12. Data and hosting

- The hosted ledger cannot be cleaned in place (by design), so v2 uses a new schema `squad2` in the same Supabase project; `squad` stays as v1's record.
- v2 gets its own Vercel project. `credit-agent-squad.vercel.app` stays as v1 until the owner decides otherwise. `c-squad.vercel.app` is frozen (`docs/DEPLOY.md`).
- `Borrower.code` stays ≤ 32 characters.

## 13. Proposed changes to the owner's design spec

1. Section 1: add innovation banking (monthly, venture-backed) beside C&I as the monitored book.
2. Rule 10 gains: "a ratio whose denominator is zero or negative is reported as not meaningful with the reason, never computed".
3. Section on covenants: add the three archetypes and funding events.

## 14. Open questions for the owner

1. The four extra innovation names and situations in 2.1: keep, or change?
2. Revenue-vs-plan floor: test revenue or ARR, and at what percentage (a common choice is 80% of plan)?
3. Watch level for RML stays 12 months for everyone, or per client in its terms?
4. Should the C&I four move to monthly too, or stay quarterly as in their v1 terms?
