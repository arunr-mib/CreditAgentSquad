/**
 * Fixture borrower: Brightwater Fastener Co. (invented). Lender: Bank of Stoic.
 * SYNTHETIC - FOR DEMONSTRATION. One coherent story across the spread and the covenant workspace:
 * the borrower's certificate adds back a restructuring charge in full, the credit agreement caps
 * the add-back, and with the cap applied the fixed charge coverage test fails.
 *
 * Inputs are typed here; every total, trailing-twelve-month value and ratio is computed below
 * with exact decimal arithmetic, so the fixture cannot show a figure that does not foot.
 */
import * as dec from '@/api/decimal';
import type {
  AgentRecommendation,
  CalcInput,
  CovenantTest,
  CycleStage,
  Fact,
  FootingCheck,
  SourcePage,
  SpreadLine,
  SpreadPeriod,
  SpreadSection,
  WorkItem,
} from '@/api/types';
import { dollars, FactBook, printedThousands } from './factbook';

export const SYNTHETIC_NOTICE = 'SYNTHETIC - FOR DEMONSTRATION';

const book = new FactBook({ factStart: 104201, calcStart: 20871, runId: 'RUN-88142' });

/* ── Borrower, documents, periods ─────────────────────────────────────── */

type PeriodId = 'fy24' | 'q3_25' | 'fy25' | 'q3_26';
const PERIOD_IDS: PeriodId[] = ['fy24', 'q3_25', 'fy25', 'q3_26'];

interface PeriodDoc {
  documentId: string;
  title: string;
  pages: { bs: number; is: number; cf: number; notes: number };
  flowLabel: string;
  pointLabel: string;
  isSubheading: string;
  bsSubheading: string;
  columnHead: string;
  comparative: PeriodId | null;
}

const DOCS: Record<PeriodId, PeriodDoc> = {
  fy24: {
    documentId: 'DOC-BWF-0031',
    title: 'Audited financial statements, year ended 31 Dec 2024',
    pages: { bs: 3, is: 4, cf: 5, notes: 14 },
    flowLabel: 'Year ended 31 Dec 2024',
    pointLabel: 'At 31 Dec 2024',
    isSubheading: 'Statements of Income · Year ended 31 December',
    bsSubheading: 'Balance Sheets · 31 December',
    columnHead: '2024',
    comparative: null,
  },
  q3_25: {
    documentId: 'DOC-BWF-0047',
    title: 'Internal financial statements, nine months ended 30 Sep 2025',
    pages: { bs: 1, is: 2, cf: 3, notes: 4 },
    flowLabel: 'Nine months ended 30 Sep 2025',
    pointLabel: 'At 30 Sep 2025',
    isSubheading: 'Statements of Income (unaudited) · Nine months ended 30 September',
    bsSubheading: 'Balance Sheets (unaudited) · 30 September',
    columnHead: '2025',
    comparative: null,
  },
  fy25: {
    documentId: 'DOC-BWF-0052',
    title: 'Audited financial statements, year ended 31 Dec 2025',
    pages: { bs: 3, is: 4, cf: 5, notes: 14 },
    flowLabel: 'Year ended 31 Dec 2025',
    pointLabel: 'At 31 Dec 2025',
    isSubheading: 'Statements of Income · Years ended 31 December',
    bsSubheading: 'Balance Sheets · 31 December',
    columnHead: '2025',
    comparative: 'fy24',
  },
  q3_26: {
    documentId: 'DOC-BWF-0068',
    title: 'Internal financial statements, nine months ended 30 Sep 2026',
    pages: { bs: 1, is: 2, cf: 3, notes: 4 },
    flowLabel: 'Nine months ended 30 Sep 2026',
    pointLabel: 'At 30 Sep 2026',
    isSubheading: 'Statements of Income (unaudited) · Nine months ended 30 September',
    bsSubheading: 'Balance Sheets (unaudited) · 30 September',
    columnHead: '2026',
    comparative: 'q3_25',
  },
};

export const periods: SpreadPeriod[] = [
  { id: 'fy24', label: 'FY 2024', periodEnd: '2024-12-31', months: 12, quality: 'audited', spreadStatus: 'confirmed', documentId: DOCS.fy24.documentId },
  { id: 'q3_25', label: '9M 2025', periodEnd: '2025-09-30', months: 9, quality: 'internal', spreadStatus: 'confirmed', documentId: DOCS.q3_25.documentId },
  { id: 'fy25', label: 'FY 2025', periodEnd: '2025-12-31', months: 12, quality: 'audited', spreadStatus: 'confirmed', documentId: DOCS.fy25.documentId },
  { id: 'q3_26', label: '9M 2026', periodEnd: '2026-09-30', months: 9, quality: 'internal', spreadStatus: 'verified', documentId: DOCS.q3_26.documentId },
];

const TTM_LABEL = 'Twelve months ended 30 Sep 2026';
const TERMS = 'Version 2, approved 9 Jan 2025';

/* ── Spreading template ci-1: lines and inputs (USD thousands as printed) ─ */

type Values = Record<PeriodId, number | null>;

interface LineDef {
  key: string;
  label: string;
  printedLabel: string;
  values?: Values;
  /** Computed lines: signed components. */
  formula?: { expression: string; terms: Array<{ key: string; sign: 1 | -1 }> };
  emphasis?: 'subtotal' | 'total';
  group?: string;
}

const v = (fy24: number | null, q3_25: number | null, fy25: number | null, q3_26: number | null): Values => ({ fy24, q3_25, fy25, q3_26 });

const IS_LINES: LineDef[] = [
  { key: 'is.revenue', label: 'Net revenue', printedLabel: 'Net sales', values: v(38420, 30150, 40870, 29480) },
  { key: 'is.cogs', label: 'Cost of goods sold', printedLabel: 'Cost of sales', values: v(28010, 22160, 30120, 22050) },
  {
    key: 'is.gross_profit',
    label: 'Gross profit',
    printedLabel: 'Gross profit',
    emphasis: 'subtotal',
    formula: {
      expression: 'Net revenue − Cost of goods sold',
      terms: [
        { key: 'is.revenue', sign: 1 },
        { key: 'is.cogs', sign: -1 },
      ],
    },
  },
  {
    key: 'is.sga',
    label: 'Selling, general and administrative',
    printedLabel: 'Selling, general and administrative expenses',
    values: v(6120, 4790, 6480, 4905),
  },
  {
    key: 'is.depreciation_amortization',
    label: 'Depreciation and amortization',
    printedLabel: 'Depreciation and amortization',
    values: v(940, 742, 1004, 774),
  },
  { key: 'is.other_operating_expense', label: 'Other operating expense', printedLabel: 'Other operating expenses', values: v(210, 165, 228, 171) },
  {
    key: 'is.nonrecurring_expense',
    label: 'Restructuring and other non-recurring charges',
    printedLabel: 'Restructuring charge',
    values: v(null, null, null, 620),
  },
  {
    key: 'is.operating_income',
    label: 'Operating income',
    printedLabel: 'Income from operations',
    emphasis: 'subtotal',
    formula: {
      expression:
        'Gross profit − Selling, general and administrative − Depreciation and amortization − Other operating expense − Restructuring and other non-recurring charges',
      terms: [
        { key: 'is.gross_profit', sign: 1 },
        { key: 'is.sga', sign: -1 },
        { key: 'is.depreciation_amortization', sign: -1 },
        { key: 'is.other_operating_expense', sign: -1 },
        { key: 'is.nonrecurring_expense', sign: -1 },
      ],
    },
  },
  { key: 'is.interest_expense', label: 'Interest expense', printedLabel: 'Interest expense', values: v(742, 548, 731, 515) },
  { key: 'is.other_income_net', label: 'Other income (expense), net', printedLabel: 'Other income, net', values: v(35, 22, 30, 18) },
  {
    key: 'is.pretax_income',
    label: 'Income before taxes',
    printedLabel: 'Income before income taxes',
    emphasis: 'subtotal',
    formula: {
      expression: 'Operating income − Interest expense + Other income (expense), net',
      terms: [
        { key: 'is.operating_income', sign: 1 },
        { key: 'is.interest_expense', sign: -1 },
        { key: 'is.other_income_net', sign: 1 },
      ],
    },
  },
  { key: 'is.income_tax_expense', label: 'Income tax expense', printedLabel: 'Provision for income taxes', values: v(584, 424, 561, 111) },
  {
    key: 'is.net_income',
    label: 'Net income',
    printedLabel: 'Net income',
    emphasis: 'total',
    formula: {
      expression: 'Income before taxes − Income tax expense',
      terms: [
        { key: 'is.pretax_income', sign: 1 },
        { key: 'is.income_tax_expense', sign: -1 },
      ],
    },
  },
];

const sum = (expression: string, keys: string[]) => ({ expression, terms: keys.map((key) => ({ key, sign: 1 as const })) });

const BS_LINES: LineDef[] = [
  { group: 'Assets', key: 'bs.cash', label: 'Cash and equivalents', printedLabel: 'Cash and cash equivalents', values: v(760, 890, 1045, 612) },
  {
    group: 'Assets',
    key: 'bs.accounts_receivable',
    label: 'Accounts receivable, net',
    printedLabel: 'Trade receivables, net',
    values: v(4620, 5120, 4910, 5340),
  },
  { group: 'Assets', key: 'bs.inventory', label: 'Inventory', printedLabel: 'Inventories', values: v(5980, 6410, 6240, 6870) },
  { group: 'Assets', key: 'bs.other_current_assets', label: 'Other current assets', printedLabel: 'Prepaid expenses and other', values: v(350, 372, 385, 410) },
  {
    group: 'Assets',
    key: 'bs.total_current_assets',
    label: 'Total current assets',
    printedLabel: 'Total current assets',
    emphasis: 'subtotal',
    formula: sum('Cash and equivalents + Accounts receivable, net + Inventory + Other current assets', [
      'bs.cash',
      'bs.accounts_receivable',
      'bs.inventory',
      'bs.other_current_assets',
    ]),
  },
  {
    group: 'Assets',
    key: 'bs.net_ppe',
    label: 'Property and equipment, net',
    printedLabel: 'Property, plant and equipment, net',
    values: v(7410, 7580, 7720, 7960),
  },
  {
    group: 'Assets',
    key: 'bs.intangibles',
    label: 'Goodwill and intangibles',
    printedLabel: 'Goodwill and intangible assets',
    values: v(1270, 1225, 1210, 1150),
  },
  { group: 'Assets', key: 'bs.other_noncurrent_assets', label: 'Other assets', printedLabel: 'Other assets', values: v(198, 210, 215, 228) },
  {
    group: 'Assets',
    key: 'bs.total_assets',
    label: 'Total assets',
    printedLabel: 'Total assets',
    emphasis: 'total',
    formula: sum('Total current assets + Property and equipment, net + Goodwill and intangibles + Other assets', [
      'bs.total_current_assets',
      'bs.net_ppe',
      'bs.intangibles',
      'bs.other_noncurrent_assets',
    ]),
  },
  { group: 'Liabilities and equity', key: 'bs.accounts_payable', label: 'Accounts payable', printedLabel: 'Trade payables', values: v(2870, 3009, 3105, 3480) },
  {
    group: 'Liabilities and equity',
    key: 'bs.accrued_liabilities',
    label: 'Accrued liabilities',
    printedLabel: 'Accrued expenses',
    values: v(1020, 1098, 1160, 1214),
  },
  { group: 'Liabilities and equity', key: 'bs.revolver', label: 'Line of credit', printedLabel: 'Revolving line of credit', values: v(1850, 2450, 2100, 2850) },
  {
    group: 'Liabilities and equity',
    key: 'bs.cpltd',
    label: 'Current portion of long-term debt',
    printedLabel: 'Current maturities of long-term debt',
    values: v(900, 900, 900, 900),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.other_current_liabilities',
    label: 'Other current liabilities',
    printedLabel: 'Other current liabilities',
    values: v(283, 305, 298, 316),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.total_current_liabilities',
    label: 'Total current liabilities',
    printedLabel: 'Total current liabilities',
    emphasis: 'subtotal',
    formula: sum('Accounts payable + Accrued liabilities + Line of credit + Current portion of long-term debt + Other current liabilities', [
      'bs.accounts_payable',
      'bs.accrued_liabilities',
      'bs.revolver',
      'bs.cpltd',
      'bs.other_current_liabilities',
    ]),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.long_term_debt',
    label: 'Long-term debt, net of current portion',
    printedLabel: 'Long-term debt, less current maturities',
    values: v(7175, 6500, 6275, 5600),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.subordinated_debt',
    label: 'Subordinated debt',
    printedLabel: 'Subordinated debt',
    values: v(null, null, null, null),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.other_noncurrent_liabilities',
    label: 'Other liabilities',
    printedLabel: 'Other long-term liabilities',
    values: v(310, 322, 331, 402),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.total_liabilities',
    label: 'Total liabilities',
    printedLabel: 'Total liabilities',
    emphasis: 'subtotal',
    formula: sum('Total current liabilities + Long-term debt, net of current portion + Subordinated debt + Other liabilities', [
      'bs.total_current_liabilities',
      'bs.long_term_debt',
      'bs.subordinated_debt',
      'bs.other_noncurrent_liabilities',
    ]),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.total_equity',
    label: 'Total equity',
    printedLabel: "Total shareholders' equity",
    values: v(6180, 7223, 7556, 7808),
  },
  {
    group: 'Liabilities and equity',
    key: 'bs.total_liabilities_and_equity',
    label: 'Total liabilities and equity',
    printedLabel: "Total liabilities and shareholders' equity",
    emphasis: 'total',
    formula: sum('Total liabilities + Total equity', ['bs.total_liabilities', 'bs.total_equity']),
  },
];

/* ── Build facts for every cell ───────────────────────────────────────── */

/** Thousands per line key per period; null means the statement has no such line. */
const thousands: Record<string, Values> = {};
/** Fact id per line key per period. */
const cellIds: Record<string, Record<string, string | null>> = {};
const statedIds: Record<string, Record<string, string | null>> = {};
export const sourcePages: Record<string, SourcePage> = {};

function buildSection(statement: 'is' | 'bs', lines: LineDef[]) {
  for (const line of lines) {
    cellIds[line.key] = {};
    statedIds[line.key] = {};
    thousands[line.key] = { fy24: null, q3_25: null, fy25: null, q3_26: null };
  }
  for (const periodId of PERIOD_IDS) {
    const doc = DOCS[periodId];
    const page = statement === 'is' ? doc.pages.is : doc.pages.bs;
    const periodLabel = statement === 'is' ? doc.flowLabel : doc.pointLabel;
    const comparative = doc.comparative;
    const pageRows: SourcePage['rows'] = [];
    let lastGroup: string | undefined;

    for (const line of lines) {
      const store = thousands[line.key] as Values;
      const ids = cellIds[line.key] as Record<string, string | null>;
      let value: number | null;
      let fact: Fact | null = null;

      if (line.formula) {
        value = line.formula.terms.reduce((total, term) => total + term.sign * ((thousands[term.key] as Values)[periodId] ?? 0), 0);
        const inputs: CalcInput[] = line.formula.terms.flatMap((term, index) => {
          const factId = (cellIds[term.key] as Record<string, string | null>)[periodId];
          const def = lines.find((candidate) => candidate.key === term.key);
          return factId && def ? [{ name: def.label, factId, op: index === 0 ? '' : term.sign === 1 ? '+' : '−' }] : [];
        });
        fact = book.calculated({
          key: line.key,
          label: line.label,
          value: dollars(value),
          periodLabel,
          formulaKey: line.key,
          formulaVersion: 'ci-1',
          expression: line.formula.expression,
          inputs,
        });
      } else {
        value = line.values?.[periodId] ?? null;
        if (value !== null) {
          const printed = printedThousands(value);
          const comparativeValue = comparative ? (line.values?.[comparative] ?? null) : null;
          const quote = `${line.printedLabel}  ${printed}${comparativeValue !== null ? `  ${printedThousands(comparativeValue)}` : ''}`;
          if (line.key === 'is.other_income_net' && periodId === 'q3_26') {
            // Entered by a person: the statement prints the components in a note, not a net line.
            fact = book.manual({
              key: line.key,
              label: line.label,
              value: dollars(value),
              periodLabel,
              enteredBy: 'Daniel Reyes, credit analyst',
              enteredAt: '6 Nov 2026, 14:22',
              reason:
                'The statement of income shows interest income and other expense in note 7 instead of a single net line. Net amount keyed from page 4, note 7; supersedes the value the agent could not verify.',
            });
          } else {
            fact = book.extracted({
              key: line.key,
              label: line.label,
              value: dollars(value),
              periodLabel,
              documentId: doc.documentId,
              documentTitle: doc.title,
              page,
              quote,
              printed,
              labelText: line.printedLabel,
              scaleAsReported: 1000,
              status: periodId === 'q3_26' ? 'verified' : 'confirmed',
            });
          }
        }
      }

      store[periodId] = value;
      ids[periodId] = fact?.id ?? null;

      // The printed total of a computed line is extracted as its own fact, for the footing check.
      let pageFactId = fact?.provenance.kind === 'extracted' ? fact.id : null;
      if (line.formula && value !== null) {
        const printed = printedThousands(value);
        const stated = book.extracted({
          key: `stated.${line.key}`,
          label: `${line.label}, as stated`,
          value: dollars(value),
          periodLabel,
          documentId: doc.documentId,
          documentTitle: doc.title,
          page,
          quote: `${line.printedLabel}  ${printed}`,
          printed,
          labelText: line.printedLabel,
          scaleAsReported: 1000,
          status: periodId === 'q3_26' ? 'verified' : 'confirmed',
        });
        (statedIds[line.key] as Record<string, string | null>)[periodId] = stated.id;
        pageFactId = stated.id;
      }

      // Facsimile row. The manually keyed line is not printed on this page.
      const printedOnPage = value !== null && !(line.key === 'is.other_income_net' && periodId === 'q3_26');
      if (printedOnPage && value !== null) {
        if (line.group && line.group !== lastGroup) {
          pageRows.push({ label: line.group, values: [], factIds: [], strong: true, gapBefore: lastGroup !== undefined });
          lastGroup = line.group;
        }
        const comparativeValue = comparative ? ((thousands[line.key] as Values)[comparative] ?? null) : null;
        pageRows.push({
          label: line.printedLabel,
          values: [printedThousands(value), ...(comparative ? [comparativeValue !== null ? printedThousands(comparativeValue) : '–'] : [])],
          factIds: [pageFactId, ...(comparative ? [null] : [])],
          strong: Boolean(line.formula),
          indent: !line.formula,
        });
      }
    }

    sourcePages[`${doc.documentId}:${page}`] = {
      documentId: doc.documentId,
      documentTitle: doc.title,
      page,
      heading: 'Brightwater Fastener Co.',
      subheading: `${statement === 'is' ? doc.isSubheading : doc.bsSubheading} · In thousands of US dollars`,
      columnHeads: [doc.columnHead, ...(comparative ? [DOCS[comparative].columnHead] : [])],
      rows: pageRows,
    };
  }
}

buildSection('is', IS_LINES);
buildSection('bs', BS_LINES);

function toSpreadLines(lines: LineDef[]): SpreadLine[] {
  return lines.map((line) => ({
    key: line.key,
    label: line.label,
    computed: Boolean(line.formula),
    emphasis: line.emphasis,
    cells: cellIds[line.key] ?? {},
    stated: line.formula ? statedIds[line.key] : undefined,
  }));
}

export const spreadSections: SpreadSection[] = [
  { id: 'is', title: 'Income statement', basis: 'Fiscal year to date', groups: [{ lines: toSpreadLines(IS_LINES) }] },
  {
    id: 'bs',
    title: 'Balance sheet',
    basis: 'At period end',
    groups: [
      { title: 'Assets', lines: toSpreadLines(BS_LINES.filter((line) => line.group === 'Assets')) },
      { title: 'Liabilities and equity', lines: toSpreadLines(BS_LINES.filter((line) => line.group === 'Liabilities and equity')) },
    ],
  },
];

const cell = (key: string, periodId: PeriodId): Fact => {
  const id = cellIds[key]?.[periodId];
  const fact = id ? book.facts[id] : undefined;
  if (!fact) throw new Error(`Fixture: no fact for ${key} in ${periodId}`);
  return fact;
};

/* ── Footing checks (spec section 4) ──────────────────────────────────── */

const manualCount = Object.values(book.facts).filter((fact) => fact.provenance.kind === 'manual').length;
const absentLines = [...IS_LINES, ...BS_LINES].filter((line) => line.values && PERIOD_IDS.some((id) => line.values?.[id] === null)).length;

export const footingChecks: FootingCheck[] = [
  {
    id: 'is-foots',
    label: 'Income statement equals its stated totals',
    detail: 'Four computed lines equal their stated totals in every period',
    result: 'pass',
    resultLabel: 'Foots',
  },
  {
    id: 'bs-foots',
    label: 'Balance sheet equals its stated totals',
    detail: 'Five computed lines equal their stated totals in every period',
    result: 'pass',
    resultLabel: 'Foots',
  },
  { id: 'bs-balances', label: 'Assets equal liabilities and equity', detail: 'All four period ends', result: 'pass', resultLabel: 'Balances' },
  {
    id: 'comparative',
    label: 'Comparative columns equal confirmed spreads',
    detail: '9M 2025 and FY 2024 as reprinted',
    result: 'pass',
    resultLabel: 'Matches',
  },
  {
    id: 'manual',
    label: 'Entered by a person: other income, 9M 2026',
    detail: 'Other income (expense), net · 9M 2026',
    result: 'info',
    resultLabel: `${manualCount} value`,
  },
  {
    id: 'absent',
    label: 'Absent from the statements, sections foot',
    detail: 'Recorded as absent because their sections foot',
    result: 'info',
    resultLabel: `${absentLines} lines`,
  },
];

/* ── Cash flow and supplemental inputs for the covenant tests ─────────── */

interface FlowInput {
  key: string;
  label: string;
  printedLabel: string;
  page: 'cf' | 'notes';
  parenthesised?: boolean;
  values: Record<'q3_26' | 'fy25' | 'q3_25', number>;
}

const FLOW_INPUTS: FlowInput[] = [
  {
    key: 'cf.capex',
    label: 'Purchases of property and equipment',
    printedLabel: 'Purchases of property and equipment',
    page: 'cf',
    parenthesised: true,
    values: { q3_26: 742, fy25: 985, q3_25: 717 },
  },
  {
    key: 'sup.financed_capex',
    label: 'Capital expenditures financed with purchase-money debt',
    printedLabel: 'Equipment acquired under purchase-money notes',
    page: 'notes',
    values: { q3_26: 250, fy25: 120, q3_25: 120 },
  },
  {
    key: 'sup.cash_taxes_paid',
    label: 'Cash paid for income taxes',
    printedLabel: 'Cash paid for income taxes',
    page: 'notes',
    values: { q3_26: 148, fy25: 540, q3_25: 407 },
  },
  {
    key: 'cf.distributions',
    label: 'Distributions to owners',
    printedLabel: 'Distributions to shareholders',
    page: 'cf',
    parenthesised: true,
    values: { q3_26: 100, fy25: 400, q3_25: 300 },
  },
  {
    key: 'sup.cash_interest_paid',
    label: 'Cash paid for interest',
    printedLabel: 'Cash paid for interest',
    page: 'notes',
    values: { q3_26: 506, fy25: 722, q3_25: 544 },
  },
  {
    key: 'sup.scheduled_principal',
    label: 'Scheduled principal payments on term debt',
    printedLabel: 'Scheduled principal payments',
    page: 'notes',
    values: { q3_26: 675, fy25: 900, q3_25: 675 },
  },
];

const flowFacts: Record<string, Record<'q3_26' | 'fy25' | 'q3_25', Fact>> = {};
for (const input of FLOW_INPUTS) {
  const perPeriod = {} as Record<'q3_26' | 'fy25' | 'q3_25', Fact>;
  for (const periodId of ['q3_26', 'fy25', 'q3_25'] as const) {
    const doc = DOCS[periodId];
    const printed = printedThousands(input.values[periodId], input.parenthesised);
    perPeriod[periodId] = book.extracted({
      key: input.key,
      label: input.label,
      value: dollars(input.values[periodId]),
      periodLabel: doc.flowLabel,
      documentId: doc.documentId,
      documentTitle: doc.title,
      page: doc.pages[input.page],
      quote: `${input.printedLabel}  ${printed}`,
      printed,
      labelText: input.printedLabel,
      scaleAsReported: 1000,
      status: periodId === 'q3_26' ? 'verified' : 'confirmed',
    });
  }
  flowFacts[input.key] = perPeriod;
}

/** Trailing twelve months = year to date + prior fiscal year − prior year to date. */
function ttm(key: string, label: string, current: Fact | null, priorYear: Fact | null, priorYtd: Fact | null): Fact {
  const zero = '0';
  const value = dec.sub(dec.add(current?.value ?? zero, priorYear?.value ?? zero), priorYtd?.value ?? zero);
  const inputs: CalcInput[] = [];
  if (current) inputs.push({ name: '9M 2026', factId: current.id, op: '' });
  if (priorYear) inputs.push({ name: 'FY 2025', factId: priorYear.id, op: '+' });
  if (priorYtd) inputs.push({ name: '9M 2025', factId: priorYtd.id, op: '−' });
  const absent = [!priorYear && 'FY 2025', !priorYtd && '9M 2025'].filter(Boolean);
  return book.calculated({
    key: `${key}.ttm`,
    label,
    value: dec.round(value, 0),
    periodLabel: TTM_LABEL,
    formulaKey: 'ttm',
    formulaVersion: 'metrics-1',
    expression: `9M 2026 + FY 2025 − 9M 2025${absent.length ? `. No such line in ${absent.join(' or ')}; recorded as absent.` : ''}`,
    inputs,
  });
}

const ttmLine = (key: string, label: string) => ttm(key, label, cell(key, 'q3_26'), cell(key, 'fy25'), cell(key, 'q3_25'));
const ttmFlow = (key: string, label: string) => {
  const facts = flowFacts[key];
  if (!facts) throw new Error(`Fixture: no flow input ${key}`);
  return ttm(key, label, facts.q3_26, facts.fy25, facts.q3_25);
};

function calc(args: {
  key: string;
  label: string;
  value: string;
  unit?: Fact['unit'];
  periodLabel?: string;
  formulaKey: string;
  expression: string;
  inputs: Array<[string, Fact, string?]>;
  terms?: boolean;
}): Fact {
  return book.calculated({
    key: args.key,
    label: args.label,
    value: args.value,
    unit: args.unit,
    periodLabel: args.periodLabel ?? TTM_LABEL,
    formulaKey: args.formulaKey,
    formulaVersion: 'metrics-1',
    expression: args.expression,
    inputs: args.inputs.map(([name, fact, op]) => ({ name, factId: fact.id, op: op ?? '' })),
    termsVersion: args.terms === false ? undefined : TERMS,
  });
}

const CREDIT_AGREEMENT = { documentId: 'DOC-BWF-0004', documentTitle: 'Credit Agreement dated 14 Jun 2023' };
const CERTIFICATE = { documentId: 'DOC-BWF-0069', documentTitle: 'Compliance certificate, quarter ended 30 Sep 2026' };

function term(args: { key: string; label: string; value: string; unit: Fact['unit']; page: number; quote: string; printed: string; labelText: string }): Fact {
  return book.extracted({ ...args, ...CREDIT_AGREEMENT, periodLabel: 'Terms in force at 30 Sep 2026', status: 'confirmed' });
}

function certified(args: {
  key: string;
  label: string;
  value: string;
  unit: Fact['unit'];
  quote: string;
  printed: string;
  labelText: string;
  scaleAsReported?: 1 | 1000;
}): Fact {
  return book.extracted({ ...args, ...CERTIFICATE, page: 2, periodLabel: 'As certified at 30 Sep 2026', status: 'verified' });
}

/* EBITDA and the capped add-back */
const niTtm = ttmLine('is.net_income', 'Net income');
const interestTtm = ttmLine('is.interest_expense', 'Interest expense');
const taxTtm = ttmLine('is.income_tax_expense', 'Income tax expense');
const daTtm = ttmLine('is.depreciation_amortization', 'Depreciation and amortization');
const ebitda = calc({
  key: 'ebitda',
  label: 'EBITDA',
  value: dec.round(dec.add(niTtm.value, interestTtm.value, taxTtm.value, daTtm.value), 0),
  formulaKey: 'ebitda',
  expression: 'Net income + Interest expense + Income tax expense + Depreciation and amortization, trailing twelve months',
  inputs: [
    ['Net income', niTtm],
    ['Interest expense', interestTtm, '+'],
    ['Income tax expense', taxTtm, '+'],
    ['Depreciation and amortization', daTtm, '+'],
  ],
  terms: false,
});

const chargeTtm = ttm('is.nonrecurring_expense', 'Restructuring charge', cell('is.nonrecurring_expense', 'q3_26'), null, null);
const addbackCap = term({
  key: 'terms.addback.restructuring.cap',
  label: 'Cap on the restructuring add-back',
  value: '250000',
  unit: 'usd',
  page: 14,
  quote:
    '“Consolidated EBITDA” means … plus (v) non-recurring restructuring charges, provided that the aggregate amount added back pursuant to this clause (v) shall not exceed $250,000 in any period of four consecutive fiscal quarters.',
  printed: '$250,000',
  labelText: 'Section 1.01, “Consolidated EBITDA”, clause (v)',
});
const addback = calc({
  key: 'addback.restructuring',
  label: 'Restructuring add-back, as capped',
  value: dec.min(chargeTtm.value, addbackCap.value),
  formulaKey: 'addback.restructuring',
  expression: 'The lower of the restructuring charge and the cap in the credit agreement',
  inputs: [
    ['Restructuring charge', chargeTtm],
    ['Cap in the credit agreement', addbackCap],
  ],
});
const adjEbitda = calc({
  key: 'adjusted_ebitda',
  label: 'Adjusted EBITDA',
  value: dec.round(dec.add(ebitda.value, addback.value), 0),
  formulaKey: 'adjusted_ebitda',
  expression: 'EBITDA + add-backs permitted by the credit agreement, each capped as stated',
  inputs: [
    ['EBITDA', ebitda],
    ['Restructuring add-back, as capped', addback, '+'],
  ],
});

/* Fixed charge coverage */
const capexTtm = ttmFlow('cf.capex', 'Capital expenditures');
const financedCapexTtm = ttmFlow('sup.financed_capex', 'Financed capital expenditures');
const unfinancedCapex = calc({
  key: 'unfinanced_capex',
  label: 'Unfinanced capital expenditures',
  value: dec.round(dec.sub(capexTtm.value, financedCapexTtm.value), 0),
  formulaKey: 'unfinanced_capex',
  expression: 'Capital expenditures − capital expenditures financed with purchase-money debt',
  inputs: [
    ['Capital expenditures', capexTtm],
    ['Financed capital expenditures', financedCapexTtm, '−'],
  ],
  terms: false,
});
const cashTaxesTtm = ttmFlow('sup.cash_taxes_paid', 'Cash taxes paid');
const distributionsTtm = ttmFlow('cf.distributions', 'Distributions to owners');
const cashInterestTtm = ttmFlow('sup.cash_interest_paid', 'Cash interest paid');
const principalTtm = ttmFlow('sup.scheduled_principal', 'Scheduled principal payments');

const fccrNumerator = calc({
  key: 'fccr.numerator',
  label: 'Cash flow available for fixed charges',
  value: dec.round(dec.sub(adjEbitda.value, unfinancedCapex.value, cashTaxesTtm.value, distributionsTtm.value), 0),
  formulaKey: 'coverage.numerator',
  expression: 'Adjusted EBITDA − Unfinanced capital expenditures − Cash taxes paid − Distributions to owners',
  inputs: [
    ['Adjusted EBITDA', adjEbitda],
    ['Unfinanced capital expenditures', unfinancedCapex, '−'],
    ['Cash taxes paid', cashTaxesTtm, '−'],
    ['Distributions to owners', distributionsTtm, '−'],
  ],
});
const fccrDenominator = calc({
  key: 'fccr.denominator',
  label: 'Fixed charges',
  value: dec.round(dec.add(cashInterestTtm.value, principalTtm.value), 0),
  formulaKey: 'coverage.denominator',
  expression: 'Cash interest paid + Scheduled principal payments',
  inputs: [
    ['Cash interest paid', cashInterestTtm],
    ['Scheduled principal payments', principalTtm, '+'],
  ],
});
const fccr = calc({
  key: 'covenant.fccr',
  label: 'Fixed charge coverage ratio',
  value: dec.div(fccrNumerator.value, fccrDenominator.value, 2),
  unit: 'ratio',
  formulaKey: 'covenant.coverage',
  expression: 'Cash flow available for fixed charges ÷ Fixed charges, rounded half-up to two places',
  inputs: [
    ['Cash flow available for fixed charges', fccrNumerator],
    ['Fixed charges', fccrDenominator, '÷'],
  ],
});
const fccrMin = term({
  key: 'terms.fccr.threshold',
  label: 'Minimum fixed charge coverage ratio',
  value: '1.20',
  unit: 'ratio',
  page: 58,
  quote: 'The Borrower shall not permit the Fixed Charge Coverage Ratio, as of the last day of any fiscal quarter, to be less than 1.20 to 1.00.',
  printed: '1.20',
  labelText: 'Section 6.12(a), Fixed Charge Coverage Ratio',
});
const fccrCert = certified({
  key: 'certificate.fccr',
  label: 'Fixed charge coverage ratio, as certified',
  value: '1.35',
  unit: 'ratio',
  quote: 'Fixed Charge Coverage Ratio: 1.35 to 1.00. Required: not less than 1.20 to 1.00. In compliance: Yes.',
  printed: '1.35',
  labelText: 'Fixed Charge Coverage Ratio',
});
const certEbitda = certified({
  key: 'certificate.adjusted_ebitda',
  label: 'Consolidated EBITDA, as certified',
  value: '3387000',
  unit: 'usd',
  quote: 'Consolidated EBITDA (including restructuring charges of 620)  3,387',
  printed: '3,387',
  labelText: 'Consolidated EBITDA',
  scaleAsReported: 1000,
});
const fccrRequired = calc({
  key: 'fccr.required_numerator',
  label: 'Cash flow needed to meet the minimum',
  value: dec.round(dec.mul(fccrMin.value, fccrDenominator.value), 0),
  formulaKey: 'coverage.required',
  expression: 'Minimum ratio × Fixed charges',
  inputs: [
    ['Minimum fixed charge coverage ratio', fccrMin],
    ['Fixed charges', fccrDenominator, '×'],
  ],
});
const fccrShortfall = calc({
  key: 'fccr.shortfall',
  label: 'Shortfall against the minimum',
  value: dec.round(dec.sub(fccrRequired.value, fccrNumerator.value), 0),
  formulaKey: 'coverage.shortfall',
  expression: 'Cash flow needed to meet the minimum − Cash flow available for fixed charges',
  inputs: [
    ['Cash flow needed to meet the minimum', fccrRequired],
    ['Cash flow available for fixed charges', fccrNumerator, '−'],
  ],
});

/* Total leverage */
const POINT = DOCS.q3_26.pointLabel;
const totalDebt = calc({
  key: 'total_debt',
  label: 'Total debt',
  value: dec.round(dec.add(cell('bs.revolver', 'q3_26').value, cell('bs.cpltd', 'q3_26').value, cell('bs.long_term_debt', 'q3_26').value), 0),
  periodLabel: POINT,
  formulaKey: 'total_debt',
  expression:
    'Line of credit + Current portion of long-term debt + Long-term debt + Subordinated debt. No subordinated debt line on the statement; recorded as absent.',
  inputs: [
    ['Line of credit', cell('bs.revolver', 'q3_26')],
    ['Current portion of long-term debt', cell('bs.cpltd', 'q3_26'), '+'],
    ['Long-term debt, net of current portion', cell('bs.long_term_debt', 'q3_26'), '+'],
  ],
  terms: false,
});
const leverage = calc({
  key: 'covenant.leverage',
  label: 'Total leverage ratio',
  value: dec.div(totalDebt.value, adjEbitda.value, 2),
  unit: 'ratio',
  periodLabel: POINT,
  formulaKey: 'covenant.leverage',
  expression: 'Total debt at period end ÷ Adjusted EBITDA, trailing twelve months, rounded half-up to two places',
  inputs: [
    ['Total debt', totalDebt],
    ['Adjusted EBITDA', adjEbitda, '÷'],
  ],
});
const leverageMax = term({
  key: 'terms.leverage.threshold',
  label: 'Maximum total leverage ratio',
  value: '3.50',
  unit: 'ratio',
  page: 58,
  quote: 'The Borrower shall not permit the Total Leverage Ratio, as of the last day of any fiscal quarter, to exceed 3.50 to 1.00.',
  printed: '3.50',
  labelText: 'Section 6.12(b), Total Leverage Ratio',
});
const leverageCert = certified({
  key: 'certificate.leverage',
  label: 'Total leverage ratio, as certified',
  value: '2.76',
  unit: 'ratio',
  quote: 'Total Leverage Ratio: 2.76 to 1.00. Required: not more than 3.50 to 1.00. In compliance: Yes.',
  printed: '2.76',
  labelText: 'Total Leverage Ratio',
});

/* Current ratio */
const tca = cell('bs.total_current_assets', 'q3_26');
const tcl = cell('bs.total_current_liabilities', 'q3_26');
const currentRatio = calc({
  key: 'covenant.current_ratio',
  label: 'Current ratio',
  value: dec.div(tca.value, tcl.value, 2),
  unit: 'ratio',
  periodLabel: POINT,
  formulaKey: 'covenant.current_ratio',
  expression: 'Total current assets ÷ Total current liabilities, rounded half-up to two places',
  inputs: [
    ['Total current assets', tca],
    ['Total current liabilities', tcl, '÷'],
  ],
});
const currentRatioMin = term({
  key: 'terms.current_ratio.threshold',
  label: 'Minimum current ratio',
  value: '1.25',
  unit: 'ratio',
  page: 58,
  quote: 'The Borrower shall maintain, as of the last day of each fiscal quarter, a Current Ratio of not less than 1.25 to 1.00.',
  printed: '1.25',
  labelText: 'Section 6.12(c), Current Ratio',
});
const currentRatioCert = certified({
  key: 'certificate.current_ratio',
  label: 'Current ratio, as certified',
  value: currentRatio.value,
  unit: 'ratio',
  quote: `Current Ratio: ${currentRatio.value} to 1.00. Required: not less than 1.25 to 1.00. In compliance: Yes.`,
  printed: currentRatio.value,
  labelText: 'Current Ratio',
});

/* Tangible net worth */
const tnw = calc({
  key: 'covenant.tangible_net_worth',
  label: 'Tangible net worth',
  value: dec.round(dec.sub(cell('bs.total_equity', 'q3_26').value, cell('bs.intangibles', 'q3_26').value), 0),
  periodLabel: POINT,
  formulaKey: 'covenant.min_tangible_net_worth',
  expression: 'Total equity − Goodwill and intangibles',
  inputs: [
    ['Total equity', cell('bs.total_equity', 'q3_26')],
    ['Goodwill and intangibles', cell('bs.intangibles', 'q3_26'), '−'],
  ],
});
const tnwMin = term({
  key: 'terms.tnw.threshold',
  label: 'Minimum tangible net worth',
  value: '6000000',
  unit: 'usd',
  page: 59,
  quote: 'The Borrower shall maintain at all times Tangible Net Worth of not less than $6,000,000.',
  printed: '$6,000,000',
  labelText: 'Section 6.12(d), Tangible Net Worth',
});
const tnwCert = certified({
  key: 'certificate.tnw',
  label: 'Tangible net worth, as certified',
  value: tnw.value,
  unit: 'usd',
  quote: `Tangible Net Worth  ${printedThousands(Number(tnw.value) / 1000)}. Required: not less than 6,000. In compliance: Yes.`,
  printed: printedThousands(Number(tnw.value) / 1000),
  labelText: 'Tangible Net Worth',
  scaleAsReported: 1000,
});

/* Capital expenditures */
const capexMax = term({
  key: 'terms.capex.threshold',
  label: 'Maximum capital expenditures',
  value: '1500000',
  unit: 'usd',
  page: 59,
  quote: 'The Borrower shall not make Capital Expenditures in excess of $1,500,000 in any period of four consecutive fiscal quarters.',
  printed: '$1,500,000',
  labelText: 'Section 6.13, Capital Expenditures',
});
const capexCert = certified({
  key: 'certificate.capex',
  label: 'Capital expenditures, as certified',
  value: capexTtm.value,
  unit: 'usd',
  quote: `Capital Expenditures, trailing four quarters  ${printedThousands(Number(capexTtm.value) / 1000)}. Permitted: not more than 1,500. In compliance: Yes.`,
  printed: printedThousands(Number(capexTtm.value) / 1000),
  labelText: 'Capital Expenditures',
  scaleAsReported: 1000,
});

/** Headroom as a percentage of the threshold; negative means the test fails. */
function headroom(id: string, name: string, value: Fact, threshold: Fact, operator: '>=' | '<='): Fact {
  const gap = operator === '>=' ? dec.sub(value.value, threshold.value) : dec.sub(threshold.value, value.value);
  return calc({
    key: `covenant.${id}.headroom`,
    label: `${name}: headroom`,
    value: dec.div(dec.mul(gap, '100'), threshold.value, 1),
    unit: 'pct',
    periodLabel: POINT,
    formulaKey: 'covenant.headroom',
    expression: operator === '>=' ? '(Calculated value − Minimum) ÷ Minimum' : '(Maximum − Calculated value) ÷ Maximum',
    inputs: [
      ['Calculated value', value],
      [operator === '>=' ? 'Minimum' : 'Maximum', threshold],
    ],
  });
}

const fccrHeadroom = headroom('fccr', 'Fixed charge coverage', fccr, fccrMin, '>=');

export const covenants: CovenantTest[] = [
  {
    id: 'fccr',
    name: 'Fixed charge coverage',
    basis: 'Trailing twelve months, tested quarterly',
    operator: '>=',
    calculatedFactId: fccr.id,
    thresholdFactId: fccrMin.id,
    headroomFactId: fccrHeadroom.id,
    certificateFactId: fccrCert.id,
    outcome: 'breach_reported_compliant',
    citation: 'Credit Agreement, section 6.12(a)',
  },
  {
    id: 'leverage',
    name: 'Total leverage',
    basis: 'Debt at period end over trailing twelve months, tested quarterly',
    operator: '<=',
    calculatedFactId: leverage.id,
    thresholdFactId: leverageMax.id,
    headroomFactId: headroom('leverage', 'Total leverage', leverage, leverageMax, '<=').id,
    certificateFactId: leverageCert.id,
    outcome: 'compliant_variance',
    citation: 'Credit Agreement, section 6.12(b)',
  },
  {
    id: 'current_ratio',
    name: 'Current ratio',
    basis: 'At period end, tested quarterly',
    operator: '>=',
    calculatedFactId: currentRatio.id,
    thresholdFactId: currentRatioMin.id,
    headroomFactId: headroom('current_ratio', 'Current ratio', currentRatio, currentRatioMin, '>=').id,
    certificateFactId: currentRatioCert.id,
    outcome: 'compliant',
    citation: 'Credit Agreement, section 6.12(c)',
  },
  {
    id: 'tnw',
    name: 'Tangible net worth',
    basis: 'At period end, tested quarterly',
    operator: '>=',
    calculatedFactId: tnw.id,
    thresholdFactId: tnwMin.id,
    headroomFactId: headroom('tnw', 'Tangible net worth', tnw, tnwMin, '>=').id,
    certificateFactId: tnwCert.id,
    outcome: 'compliant',
    citation: 'Credit Agreement, section 6.12(d)',
  },
  {
    id: 'capex',
    name: 'Capital expenditures',
    basis: 'Trailing twelve months, tested quarterly',
    operator: '<=',
    calculatedFactId: capexTtm.id,
    thresholdFactId: capexMax.id,
    headroomFactId: headroom('capex', 'Capital expenditures', capexTtm, capexMax, '<=').id,
    certificateFactId: capexCert.id,
    outcome: 'compliant',
    citation: 'Credit Agreement, section 6.13',
  },
];

/* ── Calculation breakdowns ───────────────────────────────────────────── */

export interface BreakdownRow {
  factId: string;
  label: string;
  depth: 0 | 1 | 2;
  op?: '+' | '−' | '÷' | '=';
  emphasis?: 'subtotal' | 'total';
  /** A short note under the label. May reference facts as {{fact:<id>}}. */
  note?: string;
}

export const breakdowns: Record<string, { title: string; unitNote: string; rows: BreakdownRow[] }> = {
  fccr: {
    title: 'Fixed charge coverage ratio',
    unitNote: 'USD thousands',
    rows: [
      { factId: niTtm.id, label: 'Net income', depth: 2 },
      { factId: interestTtm.id, label: 'Interest expense', depth: 2, op: '+' },
      { factId: taxTtm.id, label: 'Income tax expense', depth: 2, op: '+' },
      { factId: daTtm.id, label: 'Depreciation and amortization', depth: 2, op: '+' },
      { factId: ebitda.id, label: 'EBITDA', depth: 1, op: '=', emphasis: 'subtotal' },
      {
        factId: addback.id,
        label: 'Restructuring add-back, as capped',
        depth: 1,
        op: '+',
        note: `Charge of {{fact:${chargeTtm.id}}}, capped at {{fact:${addbackCap.id}}} by the credit agreement`,
      },
      { factId: adjEbitda.id, label: 'Adjusted EBITDA', depth: 0, op: '=', emphasis: 'subtotal' },
      { factId: unfinancedCapex.id, label: 'Unfinanced capital expenditures', depth: 0, op: '−' },
      { factId: cashTaxesTtm.id, label: 'Cash taxes paid', depth: 0, op: '−' },
      { factId: distributionsTtm.id, label: 'Distributions to owners', depth: 0, op: '−' },
      { factId: fccrNumerator.id, label: 'Cash flow available for fixed charges', depth: 0, op: '=', emphasis: 'subtotal' },
      { factId: cashInterestTtm.id, label: 'Cash interest paid', depth: 1 },
      { factId: principalTtm.id, label: 'Scheduled principal payments', depth: 1, op: '+' },
      { factId: fccrDenominator.id, label: 'Fixed charges', depth: 0, op: '÷', emphasis: 'subtotal' },
      { factId: fccr.id, label: 'Fixed charge coverage ratio', depth: 0, op: '=', emphasis: 'total' },
    ],
  },
  leverage: {
    title: 'Total leverage ratio',
    unitNote: 'USD thousands',
    rows: [
      { factId: cell('bs.revolver', 'q3_26').id, label: 'Line of credit', depth: 1 },
      { factId: cell('bs.cpltd', 'q3_26').id, label: 'Current portion of long-term debt', depth: 1, op: '+' },
      { factId: cell('bs.long_term_debt', 'q3_26').id, label: 'Long-term debt, net of current portion', depth: 1, op: '+' },
      { factId: totalDebt.id, label: 'Total debt', depth: 0, op: '=', emphasis: 'subtotal' },
      { factId: ebitda.id, label: 'EBITDA', depth: 1 },
      {
        factId: addback.id,
        label: 'Restructuring add-back, as capped',
        depth: 1,
        op: '+',
        note: `Charge of {{fact:${chargeTtm.id}}}, capped at {{fact:${addbackCap.id}}} by the credit agreement`,
      },
      { factId: adjEbitda.id, label: 'Adjusted EBITDA', depth: 0, op: '÷', emphasis: 'subtotal' },
      { factId: leverage.id, label: 'Total leverage ratio', depth: 0, op: '=', emphasis: 'total' },
    ],
  },
  current_ratio: {
    title: 'Current ratio',
    unitNote: 'USD thousands',
    rows: [
      { factId: tca.id, label: 'Total current assets', depth: 0 },
      { factId: tcl.id, label: 'Total current liabilities', depth: 0, op: '÷' },
      { factId: currentRatio.id, label: 'Current ratio', depth: 0, op: '=', emphasis: 'total' },
    ],
  },
  tnw: {
    title: 'Tangible net worth',
    unitNote: 'USD thousands',
    rows: [
      { factId: cell('bs.total_equity', 'q3_26').id, label: 'Total equity', depth: 0 },
      { factId: cell('bs.intangibles', 'q3_26').id, label: 'Goodwill and intangibles', depth: 0, op: '−' },
      { factId: tnw.id, label: 'Tangible net worth', depth: 0, op: '=', emphasis: 'total' },
    ],
  },
  capex: {
    title: 'Capital expenditures',
    unitNote: 'USD thousands',
    rows: [
      { factId: (flowFacts['cf.capex'] as Record<string, Fact>).q3_26?.id ?? '', label: 'Nine months ended 30 Sep 2026', depth: 0 },
      { factId: (flowFacts['cf.capex'] as Record<string, Fact>).fy25?.id ?? '', label: 'Year ended 31 Dec 2025', depth: 0, op: '+' },
      { factId: (flowFacts['cf.capex'] as Record<string, Fact>).q3_25?.id ?? '', label: 'Nine months ended 30 Sep 2025', depth: 0, op: '−' },
      { factId: capexTtm.id, label: 'Capital expenditures, trailing twelve months', depth: 0, op: '=', emphasis: 'total' },
    ],
  },
};

/* ── Trend: fixed charge coverage, eight quarters ─────────────────────── */

const TREND_HISTORY: Array<{ label: string; periodEnd: string; numerator: number; denominator: number }> = [
  { label: 'Q4 2024', periodEnd: '31 Dec 2024', numerator: 2331, denominator: 1575 },
  { label: 'Q1 2025', periodEnd: '31 Mar 2025', numerator: 2296, denominator: 1573 },
  { label: 'Q2 2025', periodEnd: '30 Jun 2025', numerator: 2263, denominator: 1571 },
  { label: 'Q3 2025', periodEnd: '30 Sep 2025', numerator: 2228, denominator: 1580 },
  { label: 'Q4 2025', periodEnd: '31 Dec 2025', numerator: 2247, denominator: 1622 },
  { label: 'Q1 2026', periodEnd: '31 Mar 2026', numerator: 2099, denominator: 1602 },
  { label: 'Q2 2026', periodEnd: '30 Jun 2026', numerator: 1976, denominator: 1594 },
];

export interface TrendPoint {
  label: string;
  factId: string;
  /** Plot position only; the displayed figure is always the fact. */
  plot: number;
}

export const fccrTrend: TrendPoint[] = [
  ...TREND_HISTORY.map((point) => {
    const periodLabel = `Twelve months ended ${point.periodEnd}`;
    const numerator = book.calculated({
      key: 'fccr.numerator',
      label: 'Cash flow available for fixed charges',
      value: dollars(point.numerator),
      periodLabel,
      formulaKey: 'coverage.numerator',
      formulaVersion: 'metrics-1',
      expression: 'Adjusted EBITDA − Unfinanced capital expenditures − Cash taxes paid − Distributions to owners',
      inputs: [],
    });
    const denominator = book.calculated({
      key: 'fccr.denominator',
      label: 'Fixed charges',
      value: dollars(point.denominator),
      periodLabel,
      formulaKey: 'coverage.denominator',
      formulaVersion: 'metrics-1',
      expression: 'Cash interest paid + Scheduled principal payments',
      inputs: [],
    });
    const ratio = calc({
      key: 'covenant.fccr',
      label: 'Fixed charge coverage ratio',
      value: dec.div(numerator.value, denominator.value, 2),
      unit: 'ratio',
      periodLabel,
      formulaKey: 'covenant.coverage',
      expression: 'Cash flow available for fixed charges ÷ Fixed charges, rounded half-up to two places',
      inputs: [
        ['Cash flow available for fixed charges', numerator],
        ['Fixed charges', denominator, '÷'],
      ],
    });
    return { label: point.label, factId: ratio.id, plot: Number(ratio.value) };
  }),
  { label: 'Q3 2026', factId: fccr.id, plot: Number(fccr.value) },
];

/* ── Loans, as held in the system of record ───────────────────────────── */

const CORE = { connector: 'Core loan accounting', asOf: '11 Nov 2026, close of business' };
const lineCommitment = book.system({
  key: 'loan.commitment',
  label: 'Line of credit commitment',
  value: '4000000',
  periodLabel: 'As of 11 Nov 2026',
  recordRef: 'LN-20417-R',
  ...CORE,
});
const lineDrawn = book.system({
  key: 'loan.outstanding',
  label: 'Line of credit drawn',
  value: '2975000',
  periodLabel: 'As of 11 Nov 2026',
  recordRef: 'LN-20417-R',
  ...CORE,
});
const termOutstanding = book.system({
  key: 'loan.outstanding',
  label: 'Term loan outstanding',
  value: '6425000',
  periodLabel: 'As of 11 Nov 2026',
  recordRef: 'LN-20417-T',
  ...CORE,
});

export const borrower = {
  id: 'BRW-0417',
  name: 'Brightwater Fastener Co.',
  industry: 'Industrial fasteners',
  location: 'Dayton, Ohio',
  relationshipManager: 'Maya Okafor',
  analyst: 'Daniel Reyes',
  lineCommitmentFactId: lineCommitment.id,
  lineDrawnFactId: lineDrawn.id,
  termOutstandingFactId: termOutstanding.id,
  termsVersion: TERMS,
};

/* ── Monitoring cycle ─────────────────────────────────────────────────── */

export const cycle = {
  id: 'CYC-2026Q3-0417',
  periodLabel: 'Q3 2026',
  periodEnd: '2026-09-30',
  packageReceived: '2026-10-27',
  stages: [
    { id: 'awaiting_package', label: 'Package', status: 'done', detail: 'Received 27 Oct' },
    { id: 'intake', label: 'Intake', status: 'done', detail: '4 matched' },
    { id: 'spreading', label: 'Spreading', status: 'done', detail: 'Foots, verified' },
    { id: 'covenant_testing', label: 'Covenant testing', status: 'needs_person', detail: 'Needs a person' },
    { id: 'borrowing_base', label: 'Borrowing base', status: 'pending' },
    { id: 'signals', label: 'Signals', status: 'pending' },
    { id: 'review_prep', label: 'Review prep', status: 'pending' },
    { id: 'in_review', label: 'In review', status: 'pending' },
    { id: 'actions_open', label: 'Actions', status: 'pending' },
    { id: 'closed', label: 'Closed', status: 'pending' },
  ] satisfies CycleStage[],
};

/* ── The exception and the agent's recommendation ─────────────────────── */

const f = (fact: Fact) => `{{fact:${fact.id}}}`;

export const fccrRecommendation: AgentRecommendation = {
  agent: 'Covenant Agent',
  kind: 'escalate',
  headline: 'Recommends escalate',
  body: [
    `Fixed charge coverage calculates to ${f(fccr)} against a minimum of ${f(fccrMin)}. The borrower's certificate reports ${f(fccrCert)} and states compliance.`,
    `The difference is one add-back. The certificate adds back the full restructuring charge of ${f(chargeTtm)}. The credit agreement caps that add-back at ${f(addbackCap)} in any four-quarter period, and no amendment on file changes the cap. With the cap applied, cash flow available for fixed charges is ${f(fccrNumerator)}, short of the minimum by ${f(fccrShortfall)}.`,
    'This is a breach under the terms in force, so it cannot be resolved on the evidence on file. It needs a credit officer.',
  ].join('\n\n'),
  runId: 'RUN-88213',
  writtenAt: '11 Nov 2026, 09:14',
  approved: false,
  guardrailNotes: [
    {
      layer: 'quotes',
      check: 'Quotes found on the cited pages',
      action: 'passed',
      detail: 'Three quotes located: Credit Agreement pages 14 and 58, certificate page 2.',
    },
    { layer: 'numbers', check: 'Every figure traces to a stored fact', action: 'passed', detail: 'Seven figures, all rendered from facts in scope.' },
    { layer: 'terms', check: 'Calculation used the terms in force', action: 'passed', detail: 'Version 2, approved 9 Jan 2025. No drift.' },
    {
      layer: 'policy',
      check: 'Wording limited to the allowed recommendations',
      action: 'changed',
      detail: 'A sentence proposing contact with the borrower was removed. The recommendation stays escalate.',
    },
  ],
};

export const fccrWorkItem: WorkItem = {
  id: 'WI-3107',
  type: 'covenant.reported_mismatch',
  severity: 'critical',
  borrowerId: borrower.id,
  borrowerName: borrower.name,
  stage: 'covenant_testing',
  periodLabel: 'Q3 2026',
  question: 'Fixed charge coverage fails on the bank’s calculation, but the certificate reports compliance. How should the bank respond?',
  summary: 'Breach, reported compliant',
  evidence: [
    {
      kind: 'calculated',
      label: 'Coverage calculation',
      ref: fccr.provenance.kind === 'calculated' ? fccr.provenance.calcId : undefined,
      href: '/showcase/covenants',
    },
    { kind: 'extracted', label: 'Credit Agreement', detail: 'page 14, add-back cap', href: '/showcase/covenants' },
    { kind: 'extracted', label: 'Credit Agreement', detail: 'page 58, section 6.12(a)', href: '/showcase/covenants' },
    { kind: 'extracted', label: 'Compliance certificate', detail: 'page 2', href: '/showcase/covenants' },
  ],
  decisions: [
    { id: 'escalate', label: 'Escalate to credit officer', primary: true },
    { id: 'request', label: 'Request a document' },
    { id: 'override', label: 'Decide otherwise, with a reason', needsReason: true },
  ],
  requiresSecondPerson: true,
  dueDate: '2026-11-12',
  recommendation: fccrRecommendation,
};

/** Facts the covenant workspace refers to by name. */
export const named = {
  fccr,
  fccrMin,
  fccrCert,
  fccrHeadroom,
  fccrNumerator,
  fccrDenominator,
  fccrShortfall,
  chargeTtm,
  addbackCap,
  addback,
  adjEbitda,
  certEbitda,
  leverage,
  leverageCert,
};

export const facts = book.facts;
export const documents = DOCS;
export const lineDefs = { is: IS_LINES, bs: BS_LINES };
export const cellThousands = thousands;
