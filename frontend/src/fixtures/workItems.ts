/**
 * Fixture work queue for the command centre. SYNTHETIC - FOR DEMONSTRATION. Lender: Bank of Stoic.
 * Borrower names are invented. Agent text carries figures only as {{fact:<id>}} references.
 */
import * as dec from '@/api/decimal';
import type { Fact, FactMap, WorkItem, WorkItemGroup, WorkItemType } from '@/api/types';
import { fccrWorkItem, facts as brightwaterFacts } from './brightwater';
import { FactBook } from './factbook';

const book = new FactBook({ factStart: 107640, calcStart: 21310, runId: 'RUN-88190' });
const f = (fact: Fact) => `{{fact:${fact.id}}}`;

const Q3 = 'At 30 Sep 2026';
const calcOf = (fact: Fact) => (fact.provenance.kind === 'calculated' ? fact.provenance.calcId : fact.id);

/* Tessaly Cold Storage LLC: over-advance */
const tessalyDrawn = book.system({
  key: 'loan.outstanding',
  label: 'Line of credit drawn',
  value: '3412000',
  periodLabel: 'As of 31 Oct 2026',
  connector: 'Core loan accounting',
  recordRef: 'LN-20388-R',
  asOf: '31 Oct 2026, close of business',
});
const tessalyCertBase = book.extracted({
  key: 'certificate.borrowing_base',
  label: 'Borrowing base, as certified',
  value: '3498200',
  periodLabel: 'As certified at 31 Oct 2026',
  documentId: 'DOC-TCS-0091',
  documentTitle: 'Borrowing base certificate, October 2026',
  page: 1,
  quote: 'Borrowing Base (lesser of line 9 and the Commitment)  $3,498,200',
  printed: '$3,498,200',
  labelText: 'Borrowing Base',
});
const tessalyIneligible = book.calculated({
  key: 'bb.ineligible.concentration',
  label: 'Receivables over the concentration limit',
  value: '308000',
  periodLabel: 'At 31 Oct 2026',
  formulaKey: 'bb.concentration',
  formulaVersion: 'bb-1',
  expression: 'Receivables from one account debtor above 25% of eligible receivables',
  inputs: [],
});
const tessalyBase = book.calculated({
  key: 'bb.base',
  label: 'Borrowing base, recalculated',
  value: '3236400',
  periodLabel: 'At 31 Oct 2026',
  formulaKey: 'bb.base',
  formulaVersion: 'bb-1',
  expression: 'Eligible receivables × advance rate + Eligible inventory × advance rate − Reserves',
  inputs: [{ name: 'Receivables over the concentration limit', factId: tessalyIneligible.id, op: '−' }],
});
const tessalyOver = book.calculated({
  key: 'bb.over_advance',
  label: 'Over-advance',
  value: dec.round(dec.sub(tessalyDrawn.value, tessalyBase.value), 0),
  periodLabel: 'At 31 Oct 2026',
  formulaKey: 'bb.over_advance',
  formulaVersion: 'bb-1',
  expression: 'Line of credit drawn − Borrowing base, recalculated',
  inputs: [
    { name: 'Line of credit drawn', factId: tessalyDrawn.id },
    { name: 'Borrowing base, recalculated', factId: tessalyBase.id, op: '−' },
  ],
});

/* Northgate Precision Machining: leverage breach, reported as such */
const northDebt = book.calculated({
  key: 'total_debt',
  label: 'Total debt',
  value: '14626000',
  periodLabel: Q3,
  formulaKey: 'total_debt',
  formulaVersion: 'metrics-1',
  expression: 'Line of credit + Current portion of long-term debt + Long-term debt + Subordinated debt',
  inputs: [],
});
const northEbitda = book.calculated({
  key: 'ebitda',
  label: 'EBITDA',
  value: '3550000',
  periodLabel: 'Twelve months ended 30 Sep 2026',
  formulaKey: 'ebitda',
  formulaVersion: 'metrics-1',
  expression: 'Net income + Interest expense + Income tax expense + Depreciation and amortization',
  inputs: [],
});
const northLeverage = book.calculated({
  key: 'covenant.leverage',
  label: 'Total leverage ratio',
  value: dec.div(northDebt.value, northEbitda.value, 2),
  unit: 'ratio',
  periodLabel: Q3,
  formulaKey: 'covenant.leverage',
  formulaVersion: 'metrics-1',
  expression: 'Total debt at period end ÷ EBITDA, trailing twelve months',
  inputs: [
    { name: 'Total debt', factId: northDebt.id },
    { name: 'EBITDA', factId: northEbitda.id, op: '÷' },
  ],
  termsVersion: 'Version 3, approved 2 Feb 2026',
});
const northMax = book.extracted({
  key: 'terms.leverage.threshold',
  label: 'Maximum total leverage ratio',
  value: '3.75',
  unit: 'ratio',
  periodLabel: 'Terms in force at 30 Sep 2026',
  documentId: 'DOC-NPM-0003',
  documentTitle: 'Amended and Restated Loan Agreement dated 2 Feb 2026',
  page: 41,
  quote: 'Total Leverage Ratio. Not to exceed 3.75 to 1.00 as of the end of each fiscal quarter.',
  printed: '3.75',
  labelText: 'Section 7.1(b), Total Leverage Ratio',
  status: 'confirmed',
});
const northCert = book.extracted({
  key: 'certificate.leverage',
  label: 'Total leverage ratio, as certified',
  value: northLeverage.value,
  unit: 'ratio',
  periodLabel: 'As certified at 30 Sep 2026',
  documentId: 'DOC-NPM-0077',
  documentTitle: 'Compliance certificate, quarter ended 30 Sep 2026',
  page: 1,
  quote: `Total Leverage Ratio: ${northLeverage.value} to 1.00. In compliance: No.`,
  printed: northLeverage.value,
  labelText: 'Total Leverage Ratio',
});

/* Calloway Packaging Group: amendment on file, not approved into terms */
const callowayOld = book.extracted({
  key: 'terms.leverage.threshold',
  label: 'Maximum total leverage ratio, terms in force',
  value: '3.50',
  unit: 'ratio',
  periodLabel: 'Terms version 2, in force',
  documentId: 'DOC-CPG-0002',
  documentTitle: 'Credit Agreement dated 3 Mar 2024',
  page: 52,
  quote: 'Maximum Total Leverage Ratio: 3.50 to 1.00.',
  printed: '3.50',
  labelText: 'Section 6.10(a)',
  status: 'confirmed',
});
const callowayNew = book.extracted({
  key: 'terms.leverage.threshold',
  label: 'Maximum total leverage ratio, as amended',
  value: '4.00',
  unit: 'ratio',
  periodLabel: 'Terms version 3, proposed',
  documentId: 'DOC-CPG-0058',
  documentTitle: 'Second Amendment to Credit Agreement dated 18 Sep 2026',
  page: 2,
  quote: 'Section 6.10(a) of the Credit Agreement is hereby amended by replacing “3.50 to 1.00” with “4.00 to 1.00”.',
  printed: '4.00',
  labelText: 'Section 2(b), amendment to section 6.10(a)',
  status: 'proposed',
});

/* Halvorsen Marine Supply, Inc.: section does not foot */
const halvStated = book.extracted({
  key: 'stated.bs.total_current_assets',
  label: 'Total current assets, as stated',
  value: '8412000',
  periodLabel: Q3,
  documentId: 'DOC-HMS-0064',
  documentTitle: 'Internal financial statements, nine months ended 30 Sep 2026',
  page: 1,
  quote: 'Total current assets  8,412',
  printed: '8,412',
  labelText: 'Total current assets',
  scaleAsReported: 1000,
});
const halvComputed = book.calculated({
  key: 'bs.total_current_assets',
  label: 'Total current assets, sum of lines',
  value: '8394000',
  periodLabel: Q3,
  formulaKey: 'bs.total_current_assets',
  formulaVersion: 'ci-1',
  expression: 'Cash and equivalents + Accounts receivable, net + Inventory + Other current assets',
  inputs: [],
});
const halvDiff = book.calculated({
  key: 'footing.difference',
  label: 'Footing difference',
  value: dec.round(dec.sub(halvStated.value, halvComputed.value), 0),
  periodLabel: Q3,
  formulaKey: 'footing.difference',
  formulaVersion: 'ci-1',
  expression: 'Stated total − Sum of lines',
  inputs: [
    { name: 'Total current assets, as stated', factId: halvStated.id },
    { name: 'Total current assets, sum of lines', factId: halvComputed.id, op: '−' },
  ],
});

/* Pemberton Foodservice: certificate not received */
const pembLate = book.system({
  key: 'calendar.days_late',
  label: 'Days past the due date',
  value: '13',
  unit: 'days',
  periodLabel: 'As of 12 Nov 2026',
  connector: 'Reporting calendar',
  recordRef: 'REQ-0612-CC-2026Q3',
  asOf: '12 Nov 2026',
});

/* Orrin & Vale Millwork: prior period restated */
const orrinConfirmed = book.extracted({
  key: 'bs.inventory',
  label: 'Inventory, as confirmed last year',
  value: '2960000',
  periodLabel: 'At 31 Dec 2025',
  documentId: 'DOC-OVM-0040',
  documentTitle: 'Reviewed financial statements, year ended 31 Dec 2025',
  page: 3,
  quote: 'Inventories  2,960',
  printed: '2,960',
  labelText: 'Inventories',
  scaleAsReported: 1000,
  status: 'confirmed',
});
const orrinRestated = book.extracted({
  key: 'bs.inventory',
  label: 'Inventory, comparative column',
  value: '2815000',
  periodLabel: 'At 31 Dec 2025, as reprinted',
  documentId: 'DOC-OVM-0057',
  documentTitle: 'Internal financial statements, nine months ended 30 Sep 2026',
  page: 1,
  quote: 'Inventories  3,104  2,815',
  printed: '2,815',
  labelText: 'Inventories',
  scaleAsReported: 1000,
});
const orrinDiff = book.calculated({
  key: 'restatement.difference',
  label: 'Change in the comparative',
  value: dec.round(dec.sub(orrinConfirmed.value, orrinRestated.value), 0),
  periodLabel: 'At 31 Dec 2025',
  formulaKey: 'restatement.difference',
  formulaVersion: 'ci-1',
  expression: 'Value confirmed last year − Value in the comparative column',
  inputs: [
    { name: 'Inventory, as confirmed last year', factId: orrinConfirmed.id },
    { name: 'Inventory, comparative column', factId: orrinRestated.id, op: '−' },
  ],
});

/* Kestrel Fleet Services: commentary awaiting approval */
const kestrelRev = book.calculated({
  key: 'is.revenue.ttm',
  label: 'Net revenue',
  value: '52318000',
  periodLabel: 'Twelve months ended 30 Sep 2026',
  formulaKey: 'ttm',
  formulaVersion: 'metrics-1',
  expression: '9M 2026 + FY 2025 − 9M 2025',
  inputs: [],
});
const kestrelGrowth = book.calculated({
  key: 'revenue_growth_yoy',
  label: 'Revenue growth, year on year',
  value: '6.4',
  unit: 'pct',
  periodLabel: 'Twelve months ended 30 Sep 2026',
  formulaKey: 'revenue_growth_yoy',
  formulaVersion: 'metrics-1',
  expression: '(Net revenue, trailing twelve months ÷ same period a year earlier) − 1',
  inputs: [{ name: 'Net revenue', factId: kestrelRev.id }],
});
const kestrelLev = book.calculated({
  key: 'covenant.leverage',
  label: 'Total leverage ratio',
  value: '2.41',
  unit: 'ratio',
  periodLabel: Q3,
  formulaKey: 'covenant.leverage',
  formulaVersion: 'metrics-1',
  expression: 'Total debt at period end ÷ EBITDA, trailing twelve months',
  inputs: [],
  termsVersion: 'Version 1, approved 20 May 2024',
});
const kestrelMax = book.extracted({
  key: 'terms.leverage.threshold',
  label: 'Maximum total leverage ratio',
  value: '3.25',
  unit: 'ratio',
  periodLabel: 'Terms in force at 30 Sep 2026',
  documentId: 'DOC-KFS-0001',
  documentTitle: 'Loan Agreement dated 20 May 2024',
  page: 37,
  quote: 'The ratio of Total Funded Debt to EBITDA shall not exceed 3.25 to 1.00.',
  printed: '3.25',
  labelText: 'Section 5.2(a)',
  status: 'confirmed',
});
const kestrelHeadroom = book.calculated({
  key: 'covenant.leverage.headroom',
  label: 'Total leverage: headroom',
  value: dec.div(dec.mul(dec.sub(kestrelMax.value, kestrelLev.value), '100'), kestrelMax.value, 1),
  unit: 'pct',
  periodLabel: Q3,
  formulaKey: 'covenant.headroom',
  formulaVersion: 'metrics-1',
  expression: '(Maximum − Calculated value) ÷ Maximum',
  inputs: [
    { name: 'Calculated value', factId: kestrelLev.id },
    { name: 'Maximum', factId: kestrelMax.id },
  ],
});

/* Larkspur Dental Laboratories: high signal */
const larkDsoNow = book.calculated({
  key: 'dso',
  label: 'Days sales outstanding',
  value: '61',
  unit: 'days',
  periodLabel: Q3,
  formulaKey: 'dso',
  formulaVersion: 'metrics-1',
  expression: 'Accounts receivable ÷ Net revenue, trailing twelve months × 365',
  inputs: [],
});
const larkDsoPrior = book.calculated({
  key: 'dso',
  label: 'Days sales outstanding, a year earlier',
  value: '47',
  unit: 'days',
  periodLabel: 'At 30 Sep 2025',
  formulaKey: 'dso',
  formulaVersion: 'metrics-1',
  expression: 'Accounts receivable ÷ Net revenue, trailing twelve months × 365',
  inputs: [],
});
const larkDsoChange = book.calculated({
  key: 'signal.dso_change',
  label: 'Change in days sales outstanding',
  value: dec.round(dec.sub(larkDsoNow.value, larkDsoPrior.value), 0),
  unit: 'days',
  periodLabel: Q3,
  formulaKey: 'signals.dso_up',
  formulaVersion: 'signals-1',
  expression: 'Days sales outstanding − the same a year earlier',
  inputs: [
    { name: 'Days sales outstanding', factId: larkDsoNow.id },
    { name: 'Days sales outstanding, a year earlier', factId: larkDsoPrior.id, op: '−' },
  ],
});

/* Sable Creek Aggregates: certificate mismatch */
const sableCert = book.extracted({
  key: 'certificate.eligible_ar',
  label: 'Eligible receivables, as certified',
  value: '2184000',
  periodLabel: 'As certified at 31 Oct 2026',
  documentId: 'DOC-SCA-0083',
  documentTitle: 'Borrowing base certificate, October 2026',
  page: 1,
  quote: 'Eligible Accounts Receivable  $2,184,000',
  printed: '$2,184,000',
  labelText: 'Eligible Accounts Receivable',
});
const sableCalc = book.calculated({
  key: 'bb.eligible_ar',
  label: 'Eligible receivables, recalculated',
  value: '2061500',
  periodLabel: 'At 31 Oct 2026',
  formulaKey: 'bb.eligible_ar',
  formulaVersion: 'bb-1',
  expression: 'Receivables − over 90 days − cross-aged − over concentration − excluded classes',
  inputs: [],
});
const sableDiff = book.calculated({
  key: 'bb.difference',
  label: 'Difference in eligible receivables',
  value: dec.round(dec.sub(sableCert.value, sableCalc.value), 0),
  periodLabel: 'At 31 Oct 2026',
  formulaKey: 'bb.reconcile',
  formulaVersion: 'bb-1',
  expression: 'As certified − Recalculated',
  inputs: [
    { name: 'Eligible receivables, as certified', factId: sableCert.id },
    { name: 'Eligible receivables, recalculated', factId: sableCalc.id, op: '−' },
  ],
});
const sableAvail = book.calculated({
  key: 'bb.availability',
  label: 'Availability',
  value: '412300',
  periodLabel: 'At 31 Oct 2026',
  formulaKey: 'bb.availability',
  formulaVersion: 'bb-1',
  expression: 'Lower of borrowing base and commitment − Line of credit drawn − Letters of credit',
  inputs: [],
});

/* Quillfeather Print & Label: printed figure not located */
const quillValue = book.extracted({
  key: 'bs.other_current_assets',
  label: 'Other current assets',
  value: '214000',
  periodLabel: Q3,
  documentId: 'DOC-QPL-0049',
  documentTitle: 'Compiled financial statements, nine months ended 30 Sep 2026',
  page: 2,
  quote: 'Prepaid expenses and other current assets  214',
  printed: '214',
  labelText: 'Prepaid expenses and other current assets',
  scaleAsReported: 1000,
  status: 'proposed',
});

const rec = (
  agent: string,
  kind: NonNullable<WorkItem['recommendation']>['kind'],
  headline: string,
  body: string,
  runId: string,
  writtenAt: string,
  guardrailNotes: NonNullable<WorkItem['recommendation']>['guardrailNotes'] = [],
) => ({ agent, kind, headline, body, runId, writtenAt, approved: false, guardrailNotes });

const others: WorkItem[] = [
  {
    id: 'WI-3112',
    type: 'bb.over_advance',
    severity: 'critical',
    borrowerId: 'BRW-0388',
    borrowerName: 'Tessaly Cold Storage LLC',
    stage: 'borrowing_base',
    periodLabel: 'October 2026',
    question: 'The line of credit is drawn above the recalculated borrowing base. Confirm the over-advance and choose the response.',
    summary: 'Over-advance on the line',
    evidence: [
      { kind: 'calculated', label: 'Borrowing base recalculation', ref: calcOf(tessalyBase) },
      { kind: 'extracted', label: 'Borrowing base certificate', detail: 'page 1' },
      { kind: 'system', label: 'Core loan accounting', detail: 'balance at 31 Oct', ref: 'LN-20388-R' },
    ],
    decisions: [
      { id: 'escalate', label: 'Escalate to credit officer', primary: true },
      { id: 'request', label: 'Request a corrected certificate' },
    ],
    requiresSecondPerson: true,
    dueDate: '2026-11-12',
    recommendation: rec(
      'Borrowing Base Agent',
      'escalate',
      'Recommends escalate',
      `The borrowing base recalculates to ${f(tessalyBase)} against ${f(tessalyDrawn)} drawn, an over-advance of ${f(tessalyOver)}. The certificate shows a base of ${f(tessalyCertBase)}.\n\nThe difference is ${f(tessalyIneligible)} of receivables from one customer above the concentration limit, which the certificate counts as eligible.`,
      'RUN-88231',
      '11 Nov 2026, 16:40',
      [
        { layer: 'numbers', check: 'Every figure traces to a stored fact', action: 'passed', detail: 'Five figures, all rendered from facts in scope.' },
        { layer: 'policy', check: 'Over-advance is never resolved by an agent', action: 'passed', detail: 'Policy requires a person for every over-advance.' },
      ],
    ),
  },
  {
    id: 'WI-3098',
    type: 'covenant.breach',
    severity: 'high',
    borrowerId: 'BRW-0402',
    borrowerName: 'Northgate Precision Machining',
    stage: 'covenant_testing',
    periodLabel: 'Q3 2026',
    question: 'Total leverage is above the maximum, and the certificate reports the same result. How should the bank respond?',
    summary: 'Leverage above maximum',
    evidence: [
      { kind: 'calculated', label: 'Total leverage calculation', ref: calcOf(northLeverage) },
      { kind: 'extracted', label: 'Amended and Restated Loan Agreement', detail: 'page 41, section 7.1(b)' },
      { kind: 'extracted', label: 'Compliance certificate', detail: 'page 1' },
    ],
    decisions: [
      { id: 'escalate', label: 'Escalate to credit officer', primary: true },
      { id: 'request', label: 'Request a document' },
    ],
    requiresSecondPerson: true,
    dueDate: '2026-11-13',
    recommendation: rec(
      'Covenant Agent',
      'escalate',
      'Recommends escalate',
      `Total leverage calculates to ${f(northLeverage)} against a maximum of ${f(northMax)}. The certificate reports ${f(northCert)} and states non-compliance, so the bank and the borrower agree on the result.\n\nNothing on file changes the maximum for this quarter.`,
      'RUN-88207',
      '10 Nov 2026, 11:02',
      [{ layer: 'numbers', check: 'Every figure traces to a stored fact', action: 'passed', detail: 'Three figures, all rendered from facts in scope.' }],
    ),
  },
  {
    id: 'WI-3101',
    type: 'terms.unapproved_amendment',
    severity: 'high',
    borrowerId: 'BRW-0371',
    borrowerName: 'Calloway Packaging Group',
    stage: 'covenant_testing',
    periodLabel: 'Q3 2026',
    question: 'A second amendment is on file and changes the leverage maximum, but it is not approved into terms. Review the proposed terms version?',
    summary: 'Amendment not in terms',
    evidence: [
      { kind: 'extracted', label: 'Second Amendment to Credit Agreement', detail: 'page 2, section 2(b)' },
      { kind: 'extracted', label: 'Credit Agreement', detail: 'page 52, section 6.10(a)' },
    ],
    decisions: [
      { id: 'review', label: 'Review proposed terms', primary: true },
      { id: 'reject', label: 'Record as not in force', needsReason: true },
    ],
    requiresSecondPerson: true,
    dueDate: '2026-11-13',
    recommendation: rec(
      'Terms Agent',
      'draft',
      'Drafted a proposed terms version',
      `The Second Amendment replaces the maximum total leverage ratio of ${f(callowayOld)} with ${f(callowayNew)}. The quote was found on the cited page.\n\nUntil a second person approves the new version, this quarter's test runs on the terms in force.`,
      'RUN-88174',
      '9 Nov 2026, 15:26',
      [{ layer: 'quotes', check: 'Quotes found on the cited pages', action: 'passed', detail: 'Both clauses located.' }],
    ),
  },
  {
    id: 'WI-3089',
    type: 'spread.does_not_foot',
    severity: 'high',
    borrowerId: 'BRW-0356',
    borrowerName: 'Halvorsen Marine Supply, Inc.',
    stage: 'spreading',
    periodLabel: 'Q3 2026',
    question: 'Total current assets as printed does not equal the sum of its lines. Which is right?',
    summary: 'Current assets do not foot',
    evidence: [
      { kind: 'extracted', label: 'Internal financial statements', detail: 'page 1, balance sheet' },
      { kind: 'calculated', label: 'Footing check', ref: calcOf(halvDiff) },
    ],
    decisions: [
      { id: 'open', label: 'Open the spread', primary: true },
      { id: 'request', label: 'Request restated statements' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-14',
    recommendation: rec(
      'Spreading Agent',
      'abstain',
      'Abstains',
      `The printed total of ${f(halvStated)} differs from the sum of the extracted lines, ${f(halvComputed)}, by ${f(halvDiff)}. No line on the page accounts for the difference, so no value was changed.`,
      'RUN-88160',
      '9 Nov 2026, 10:48',
    ),
  },
  {
    id: 'WI-3094',
    type: 'covenant.cannot_test',
    severity: 'medium',
    borrowerId: 'BRW-0349',
    borrowerName: 'Ridgeline Industrial Laundry',
    stage: 'covenant_testing',
    periodLabel: 'Q3 2026',
    question: 'Fixed charge coverage cannot be tested: scheduled principal payments are not stated in the package. Request the debt schedule?',
    summary: 'Coverage cannot be tested',
    evidence: [{ kind: 'extracted', label: 'Internal financial statements', detail: 'page 4, notes' }],
    decisions: [
      { id: 'request', label: 'Request the debt schedule', primary: true },
      { id: 'enter', label: 'Enter the value with a citation' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-14',
    recommendation: rec(
      'Covenant Agent',
      'request',
      'Recommends request',
      'The notes page omits the schedule of principal payments on term debt. The test needs that input, and a missing input is not treated as zero.',
      'RUN-88198',
      '10 Nov 2026, 08:31',
    ),
  },
  {
    id: 'WI-3066',
    type: 'intake.missing_document',
    severity: 'medium',
    borrowerId: 'BRW-0333',
    borrowerName: 'Pemberton Foodservice',
    stage: 'awaiting_package',
    periodLabel: 'Q3 2026',
    question: 'The compliance certificate has not been received. Review the reminder before it goes to the outbox?',
    summary: 'Certificate not received',
    evidence: [{ kind: 'system', label: 'Reporting calendar', detail: 'certificate requirement', ref: 'REQ-0612-CC-2026Q3' }],
    decisions: [
      { id: 'review', label: 'Review the reminder draft', primary: true },
      { id: 'received', label: 'Mark as received' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-09',
    recommendation: rec(
      'Intake Agent',
      'request',
      'Recommends request',
      `The financial statements arrived without the compliance certificate, which is now ${f(pembLate)} past its due date. A reminder is drafted in the outbox. Nothing has been sent.`,
      'RUN-88121',
      '9 Nov 2026, 07:05',
    ),
  },
  {
    id: 'WI-3091',
    type: 'spread.restatement',
    severity: 'medium',
    borrowerId: 'BRW-0364',
    borrowerName: 'Orrin & Vale Millwork',
    stage: 'spreading',
    periodLabel: 'Q3 2026',
    question: 'The comparative column differs from the spread confirmed last year. Accept the restated values?',
    summary: 'Prior period restated',
    evidence: [
      { kind: 'extracted', label: 'Reviewed financial statements, 2025', detail: 'page 3' },
      { kind: 'extracted', label: 'Internal financial statements, 9M 2026', detail: 'page 1' },
    ],
    decisions: [
      { id: 'compare', label: 'Compare the two spreads', primary: true },
      { id: 'keep', label: 'Keep the confirmed values', needsReason: true },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-16',
    recommendation: rec(
      'Spreading Agent',
      'abstain',
      'Abstains',
      `Inventory at the prior year end was confirmed at ${f(orrinConfirmed)}. The comparative column now prints ${f(orrinRestated)}, lower by ${f(orrinDiff)}. The statements do not explain the change.`,
      'RUN-88166',
      '9 Nov 2026, 13:12',
    ),
  },
  {
    id: 'WI-3103',
    type: 'review.commentary_approval',
    severity: 'medium',
    borrowerId: 'BRW-0318',
    borrowerName: 'Kestrel Fleet Services',
    stage: 'review_prep',
    periodLabel: 'Q3 2026',
    question: 'Review commentary for the Q3 sheet is drafted. Approve it, or edit first?',
    summary: 'Commentary to approve',
    evidence: [{ kind: 'calculated', label: 'Covenant tests, Q3 2026', ref: calcOf(kestrelLev) }],
    decisions: [
      { id: 'approve', label: 'Approve commentary', primary: true },
      { id: 'edit', label: 'Edit first' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-17',
    recommendation: rec(
      'Review Agent',
      'draft',
      'Drafted review commentary',
      `Revenue for the trailing twelve months is ${f(kestrelRev)}, up ${f(kestrelGrowth)} on the prior year. Total leverage is ${f(kestrelLev)} against a maximum of ${f(kestrelMax)}, headroom of ${f(kestrelHeadroom)}. All covenants are compliant and agree with the certificate. No signals this quarter.`,
      'RUN-88219',
      '11 Nov 2026, 12:20',
    ),
  },
  {
    id: 'WI-3105',
    type: 'signal.high',
    severity: 'medium',
    borrowerId: 'BRW-0327',
    borrowerName: 'Larkspur Dental Laboratories',
    stage: 'signals',
    periodLabel: 'Q3 2026',
    question: 'Receivable days rose sharply over the year. Acknowledge the signal?',
    summary: 'Receivable days up sharply',
    evidence: [{ kind: 'calculated', label: 'Signal rule: receivable days up', ref: calcOf(larkDsoChange) }],
    decisions: [
      { id: 'ack', label: 'Acknowledge the signal', primary: true },
      { id: 'agenda', label: 'Add to the review agenda' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-17',
    recommendation: rec(
      'Early Warning Agent',
      'draft',
      'Ranked first of three signals',
      `Days sales outstanding is ${f(larkDsoNow)}, up ${f(larkDsoChange)} from ${f(larkDsoPrior)} a year earlier. Revenue is flat over the same period, so the rise is slower collection, not growth.`,
      'RUN-88224',
      '11 Nov 2026, 14:03',
    ),
  },
  {
    id: 'WI-3109',
    type: 'bb.certificate_mismatch',
    severity: 'medium',
    borrowerId: 'BRW-0341',
    borrowerName: 'Sable Creek Aggregates',
    stage: 'borrowing_base',
    periodLabel: 'October 2026',
    question: 'Eligible receivables on the certificate differ from the recalculation. Request a corrected certificate?',
    summary: 'Certificate mismatch',
    evidence: [
      { kind: 'extracted', label: 'Borrowing base certificate', detail: 'page 1' },
      { kind: 'calculated', label: 'Eligible receivables recalculation', ref: calcOf(sableCalc) },
    ],
    decisions: [
      { id: 'request', label: 'Request a corrected certificate', primary: true },
      { id: 'accept', label: 'Accept the recalculation' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-18',
    recommendation: rec(
      'Borrowing Base Agent',
      'request',
      'Recommends request',
      `The certificate shows eligible receivables of ${f(sableCert)}. The recalculation gives ${f(sableCalc)}, lower by ${f(sableDiff)}: one invoice is past the age limit. Availability stays positive at ${f(sableAvail)}.`,
      'RUN-88228',
      '11 Nov 2026, 15:17',
    ),
  },
  {
    id: 'WI-3110',
    type: 'package.release',
    severity: 'low',
    borrowerId: 'BRW-0309',
    borrowerName: 'Marlowe Street Bakeries',
    stage: 'review_prep',
    periodLabel: 'Q3 2026',
    question: 'The Q3 review package is assembled. Release it to the review room?',
    summary: 'Package ready to release',
    evidence: [{ kind: 'system', label: 'Review package', detail: 'six files, frozen on release', ref: 'PKG-0309-2026Q3' }],
    decisions: [{ id: 'release', label: 'Review and release', primary: true }],
    requiresSecondPerson: true,
    dueDate: '2026-11-19',
    recommendation: null,
  },
  {
    id: 'WI-3111',
    type: 'spread.value_unverified',
    severity: 'low',
    borrowerId: 'BRW-0382',
    borrowerName: 'Quillfeather Print & Label',
    stage: 'spreading',
    periodLabel: 'Q3 2026',
    question: 'One printed figure could not be found on the page. Confirm or correct it?',
    summary: 'Printed figure not located',
    evidence: [{ kind: 'extracted', label: 'Compiled financial statements', detail: 'page 2, balance sheet', ref: quillValue.id }],
    decisions: [
      { id: 'open', label: 'Open the page', primary: true },
      { id: 'correct', label: 'Correct with a citation' },
    ],
    requiresSecondPerson: false,
    dueDate: '2026-11-20',
    recommendation: rec(
      'Spreading Agent',
      'abstain',
      'Abstains',
      `The value ${f(quillValue)} was read for other current assets, but the printed text was not found where the scan is faint. It stays proposed until a person confirms it.`,
      'RUN-88169',
      '9 Nov 2026, 13:40',
    ),
  },
];

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 } as const;

/** The queue, ordered by severity and then by due date. */
export const workItems: WorkItem[] = [fccrWorkItem, ...others].sort(
  (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || a.dueDate.localeCompare(b.dueDate) || a.id.localeCompare(b.id),
);

export const workItemFacts: FactMap = { ...brightwaterFacts, ...book.facts };

export const workItemGroup: Record<WorkItemType, WorkItemGroup> = {
  'intake.missing_document': 'intake',
  'intake.unclassified': 'intake',
  'spread.value_unverified': 'spreading',
  'spread.does_not_foot': 'spreading',
  'spread.restatement': 'spreading',
  'spread.image_only': 'spreading',
  'terms.approval_needed': 'terms',
  'terms.unapproved_amendment': 'terms',
  'covenant.breach': 'covenant',
  'covenant.reported_mismatch': 'covenant',
  'reading.review': 'spreading',
  'covenant.reported_breach_unconfirmed': 'covenant',
  'fact.correction_changed_outcome': 'covenant',
  'covenant.cannot_test': 'covenant',
  'bb.over_advance': 'borrowing_base',
  'bb.certificate_mismatch': 'borrowing_base',
  'signal.high': 'signals',
  'review.commentary_approval': 'review',
  'package.release': 'review',
};

export const workItemGroupLabel: Record<WorkItemGroup, string> = {
  covenant: 'Covenant',
  spreading: 'Spreading',
  terms: 'Terms',
  borrowing_base: 'Borrowing base',
  intake: 'Intake',
  signals: 'Signals',
  review: 'Review',
};

export const workItemTypeLabel: Record<WorkItemType, string> = {
  'intake.missing_document': 'Missing document',
  'intake.unclassified': 'Unclassified document',
  'spread.value_unverified': 'Value not verified',
  'spread.does_not_foot': 'Section does not foot',
  'spread.restatement': 'Restated prior period',
  'spread.image_only': 'Image-only page',
  'terms.approval_needed': 'Terms awaiting approval',
  'terms.unapproved_amendment': 'Amendment not approved into terms',
  'covenant.breach': 'Covenant breach',
  'covenant.reported_mismatch': 'Covenant breach, certificate reports compliant',
  'reading.review': 'Reading to confirm',
  'covenant.reported_breach_unconfirmed': 'Certificate reports a breach the calculation does not show',
  'fact.correction_changed_outcome': 'Corrected figure changed a covenant outcome',
  'covenant.cannot_test': 'Covenant cannot be tested',
  'bb.over_advance': 'Over-advance',
  'bb.certificate_mismatch': 'Borrowing base certificate mismatch',
  'signal.high': 'High-severity signal',
  'review.commentary_approval': 'Commentary awaiting approval',
  'package.release': 'Package release',
};

/** Portfolio counts for the summary strip. Counts of records, not facts. */
export const portfolioSummary = {
  asOf: '2026-11-12',
  lender: 'Bank of Stoic',
  borrowers: 21,
  cycles: {
    inProgress: 17,
    byState: [
      { label: 'Need a person', count: 13 },
      { label: 'Running', count: 2 },
      { label: 'In review', count: 2 },
      { label: 'Closed', count: 4 },
    ],
  },
  packages: {
    dueThisWeek: 5,
    byState: [
      { label: 'Overdue', count: 2, attention: true },
      { label: 'Received', count: 14 },
      { label: 'Not yet due', count: 5 },
    ],
  },
};
