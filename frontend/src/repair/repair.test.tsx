import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser, FactSummary, HeldCell, Recalculation, Spread, WorkItemDetail } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { HeldFigures } from '@/screens/work/HeldFigures';
import { SourceContext, type SourceRef } from '@/source/context';
import { parseFigureInput, readBack } from './FigureForm';
import { describeLine, footingProblems, heldCells, needsPerson, primaryAction, spreadContext, swappedPairs, whatCodeWillDo, whyHeld } from './held';
import { RecalculationNote } from './RecalculationNote';
import { outcomeLabel, recalculationSummary } from './recalculation';

const NOTHING: Recalculation = { retired: 0, totals: null, metrics: [], covenants: [] };

describe('what was recalculated, in words', () => {
  it('says so plainly when nothing had been calculated from the figure', () => {
    expect(recalculationSummary(NOTHING)).toEqual({
      sentences: ['Nothing had been calculated from the old figure, so nothing was retired or recalculated.'],
      changes: [],
      needsAttention: false,
    });
    expect(recalculationSummary(NOTHING, {}, 'this figure').sentences[0]).toBe('Nothing had been calculated from this figure, so nothing was retired or recalculated.');
  });

  it('counts retired results in the singular and the plural', () => {
    expect(recalculationSummary({ ...NOTHING, retired: 1 }).sentences).toEqual(['1 result calculated from the old figure was retired.']);
    expect(recalculationSummary({ ...NOTHING, retired: 14 }).sentences).toEqual(['14 results calculated from the old figure were retired.']);
  });

  it('says whether totals were recalculated, and never claims they foot when they do not', () => {
    const recalculated = recalculationSummary({ ...NOTHING, retired: 6, totals: 'recalculated' });
    expect(recalculated.sentences).toContain('Statement totals were recalculated from the figures now on file, and the statements foot.');
    expect(recalculated.needsAttention).toBe(false);

    const broken = recalculationSummary({ ...NOTHING, retired: 6, totals: 'does_not_foot' });
    expect(broken.sentences).toContain('The statements no longer foot, so no totals are stored. That question is now in the work queue for a person.');
    expect(broken.sentences.join(' ')).not.toMatch(/statements foot\./);
    expect(broken.needsAttention).toBe(true);

    const unknown = recalculationSummary({ ...NOTHING, retired: 2, totals: 'not_recalculated' });
    expect(unknown.sentences).toContain('Statement totals were not recalculated: the length of the period could not be worked out.');
    expect(unknown.needsAttention).toBe(true);
  });

  it('separates metrics that were measured again from those that stay absent', () => {
    const summary = recalculationSummary({
      ...NOTHING,
      retired: 3,
      metrics: [
        { key: 'metric.leverage', period_end: '2026-09-30', fact_id: 'f-1' },
        { key: 'metric.dso', period_end: '2026-09-30', fact_id: 'f-2' },
        { key: 'metric.ebitda_margin', period_end: '2026-09-30', fact_id: null },
      ],
    });
    expect(summary.sentences).toContain('2 review metrics were calculated again.');
    expect(summary.sentences).toContain('1 review metric could not be measured from the figures on file and stays absent.');
  });

  it('names each covenant whose outcome changed, before and after, and only counts the rest', () => {
    const summary = recalculationSummary(
      {
        retired: 9,
        totals: 'recalculated',
        metrics: [],
        covenants: [
          { facility_id: 'l-1', period_end: '2026-09-30', covenant_id: 'total_leverage', before: 'compliant', after: 'breach' },
          { facility_id: 'l-1', period_end: '2026-09-30', covenant_id: 'fixed_charge_coverage', before: 'compliant', after: 'compliant' },
          { facility_id: 'l-1', period_end: '2026-09-30', covenant_id: 'min_liquidity', before: null, after: 'cannot_test' },
        ],
      },
      { total_leverage: 'Total Leverage Ratio' },
    );
    expect(summary.changes.map((change) => change.sentence)).toEqual(['Total Leverage Ratio, Q3 2026: Compliant → Breach', 'Min liquidity, Q3 2026: Not tested before → Cannot test']);
    expect(summary.sentences).toContain('1 covenant test was run again with the same outcome.');
    expect(summary.sentences).toContain('2 covenant outcomes changed. Earlier decisions and commentary used the old outcomes.');
    // The summary restates what code did; it never says the change was reviewed or resolved.
    expect(summary.sentences.join(' ')).not.toMatch(/resolved|reviewed|approved/i);
  });

  it('shows an outcome it does not know in its own words', () => {
    expect(outcomeLabel('breach_reported_compliant')).toBe('Breach, reported compliant');
    expect(outcomeLabel('waived_for_period')).toBe('Waived for period');
    expect(outcomeLabel(null)).toBe('Not tested before');
  });
});

describe('a figure typed by a person', () => {
  it('accepts grouped digits and a sign, and refuses anything that is not a plain number', () => {
    expect(parseFigureInput('1,236,000')).toBe('1236000');
    expect(parseFigureInput(' -620000.50 ')).toBe('-620000.50');
    expect(parseFigureInput('+42')).toBe('42');
    expect(parseFigureInput('1.2m')).toBeNull();
    expect(parseFigureInput('(620)')).toBeNull();
    expect(parseFigureInput('')).toBeNull();
  });

  it('reads the value back as it will be stored, and in thousands when the statement is printed that way', () => {
    expect(readBack('1236000', 'usd', 1000)).toBe('Will be stored as $1,236,000, shown on a statement in thousands as 1,236.');
    expect(readBack('-620000', 'usd')).toBe('Will be stored as ($620,000).');
    expect(readBack('0.072', 'pct')).toBe('Will be stored as 7.2%.');
    expect(readBack('3.25', 'ratio')).toBe('Will be stored as 3.25x.');
  });
});

/* ── The held-figures panel ───────────────────────────────────────────── */

const fact = (over: Partial<FactSummary>): FactSummary => ({
  id: 'f-ap',
  key: 'bs.accrued_liabilities',
  label: 'Accrued liabilities',
  value: '8067000',
  unit: 'usd',
  kind: 'extracted',
  status: 'proposed',
  period_end: '2026-09-30',
  months: 0,
  borrower_id: 'b-1',
  document_id: 'd-1',
  page: 2,
  calc_run_id: null,
  ...over,
});

/** The row printed "Accounts payable", filed under accrued liabilities: its label names another line. */
const PAYABLE_ROW = {
  key: 'bs.accrued_liabilities',
  page: 2,
  printed_figure: '8,067',
  printed_label: 'Accounts payable',
  row_label: 'Accounts payable',
  reason: 'mapping_doubt',
  detail: "the label 'Accounts payable' reads as 'Accounts payable', not 'Accrued liabilities'",
  fact_id: 'f-ap',
  reads_as: { key: 'bs.accounts_payable', value: '8067000' },
};
/** The row printed "Accrued liabilities", filed under accounts payable: with the row above, a swapped pair. */
const ACCRUED_ROW = {
  key: 'bs.accounts_payable',
  page: 2,
  printed_figure: '1,966',
  printed_label: 'Accrued liabilities',
  row_label: 'Accrued liabilities',
  reason: 'mapping_doubt',
  detail: "the label 'Accrued liabilities' reads as 'Accrued liabilities', not 'Accounts payable'",
  fact_id: 'f-al',
  reads_as: { key: 'bs.accrued_liabilities', value: '1966000' },
};
const INTEREST_ROW = { key: 'is.interest_expense', page: 3, printed_figure: '1,236', printed_label: 'Interest expense', row_label: '', reason: 'not_found', detail: "'1,236' is not on the cited page", fact_id: null, reads_as: null };
const TOTAL_ROW = { key: 'stated.bs.total_assets', page: 2, printed_figure: '64,410', printed_label: 'Total assets', row_label: '', reason: 'not_found', detail: null, fact_id: null, reads_as: null };

const item = (over: Partial<WorkItemDetail> = {}, cells: unknown[] = [PAYABLE_ROW, INTEREST_ROW, TOTAL_ROW]): WorkItemDetail => ({
  id: 'w-1',
  borrower_id: 'b-1',
  borrower_name: 'Harrowgate Precision Components, Inc.',
  facility_id: null,
  cycle_id: 'c-1',
  stage: 'spreading',
  item_type: 'spread.value_unverified',
  severity: 'medium',
  title: 'Interim statements: 2 figure(s) could not be verified on the page',
  question: 'These figures could not be found on the cited page exactly as reported. Confirm or correct each one?',
  allowed_decisions: ['values_confirmed', 'values_corrected', 'request_new_document'],
  blocks_stage: true,
  requires_second_person: false,
  required_permission: 'confirm_spread',
  prepared_by_id: null,
  due_date: null,
  status: 'open',
  decision: null,
  decision_reason: null,
  decided_by: null,
  decided_at: null,
  agent_run_id: null,
  created_at: '2026-11-17T08:00:00',
  recommendation: null,
  guardrail_notes: [],
  evidence: { document_id: 'd-1', spread: { document_id: 'd-1', period_end: '2026-09-30', months: 9, scale: 1000, absent: [] }, cells },
  ...over,
});

const heldCell = (factId: string, value: string) => ({ '2026-09-30': { fact_id: factId, value, kind: 'extracted' as const, status: 'proposed' as const, usable: false } });

const spread = (over: Record<string, Spread['lines'][number]['cells']> = {}): Spread => ({
  template: 'standard',
  periods: [{ period_end: '2026-09-30', months: 9 }],
  lines: [
    { key: 'is.interest_expense', label: 'Interest expense', statement: 'is', computed: false, cells: {} },
    { key: 'bs.accounts_payable', label: 'Accounts payable', statement: 'bs', computed: false, cells: over['bs.accounts_payable'] ?? {} },
    { key: 'bs.accrued_liabilities', label: 'Accrued liabilities', statement: 'bs', computed: false, cells: heldCell('f-ap', '8067000') },
    { key: 'bs.revolver', label: 'Line of credit', statement: 'bs', computed: false, cells: over['bs.revolver'] ?? {} },
    { key: 'cf.capex', label: 'Purchases of property and equipment', statement: 'cf', computed: false, cells: {} },
    { key: 'cf.other_investing', label: 'Other investing', statement: 'cf', computed: false, cells: over['cf.other_investing'] ?? {} },
    { key: 'bs.total_assets', label: 'Total assets', statement: 'bs', computed: true, cells: over['bs.total_assets'] ?? {} },
  ],
});
const SPREAD = spread();

type Route = { status?: number; body: unknown };

/** Routes are matched by method and the start of the address, in the order given. Every call is recorded with its body. */
function mockApi(routes: Record<string, Route>) {
  const calls: Array<{ method: string; url: string; body: unknown }> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET';
      calls.push({ method, url, body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined });
      const hit = Object.entries(routes).find(([route]) => `${method} ${url}`.startsWith(route));
      const status = hit?.[1].status ?? (hit ? 200 : 404);
      return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(hit?.[1].body ?? { detail: 'Not found' }) } as Response;
    }),
  );
  return calls;
}

const READS: Record<string, Route> = {
  'GET /api/v1/borrowers/b-1/spread': { body: SPREAD },
  'GET /api/v1/borrowers/b-1/documents': { body: [{ id: 'd-1', title: 'Interim financial statements, Q3 2026' }] },
  'GET /api/v1/ui/facts': { body: { 'f-ap': fact({}) } },
  'GET /api/v1/ui/borrowers/b-1/covenants': { body: { tests: [], facts: {} } },
};

/** The two rows filed under each other's lines, both stored and both held. */
const SWAPPED: Record<string, Route> = {
  ...READS,
  'GET /api/v1/borrowers/b-1/spread': { body: spread({ 'bs.accounts_payable': heldCell('f-al', '1966000') }) },
  'GET /api/v1/ui/facts': { body: { 'f-ap': fact({}), 'f-al': fact({ id: 'f-al', key: 'bs.accounts_payable', label: 'Accounts payable', value: '1966000' }) } },
};

const changed = (over: Partial<FactSummary>, recalculation: Recalculation = NOTHING) => ({ ...fact({ kind: 'manual', status: 'confirmed', ...over }), recalculation });
const posts = (calls: Array<{ method: string; url: string; body: unknown }>) => calls.filter((call) => call.method === 'POST').map(({ url, body }) => ({ url, body }));

const analyst: ApiUser = { id: 'u-1', email: 'analyst@bankofstoic.example', name: 'Priya Raman', title: 'Credit analyst', role: 'analyst', permissions: ['view', 'confirm_spread'] };
const officer: ApiUser = { ...analyst, id: 'u-2', name: 'Helen Strand', role: 'credit_officer', permissions: ['view', 'decide_breach'] };

function renderHeld(work: WorkItemDetail, user: ApiUser = analyst, open: (ref: SourceRef) => void = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = { user, status: 'signed-in' as const, can: (permission: string) => user.permissions.includes(permission), signIn: async () => user, signOut: async () => {}, retry: () => {} };
  const wrap = (children: ReactNode) => (
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <SourceContext.Provider value={{ open, close: () => {}, current: null }}>{children}</SourceContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
  return render(wrap(<HeldFigures item={work} code="harrowgate-precision" />));
}

const rowOf = (key: string) => document.querySelector(`[data-held-row="${key}"]`) as HTMLElement;
const primaries = (scope: HTMLElement) => [...scope.querySelectorAll('[data-primary]')].map((button) => button.textContent);
const text = (scope: HTMLElement, selector: string) => scope.querySelector(selector)?.textContent ?? '';

afterEach(() => vi.unstubAllGlobals());

describe('reading a held spread’s evidence', () => {
  it('lists the held cells and leaves out anything malformed', () => {
    const cells = heldCells({ cells: [{ key: 'bs.cash', page: 2, printed_figure: '100', reason: 'ambiguous', fact_id: 'f-1' }, { page: 2 }, 'nonsense', null] });
    expect(cells).toEqual([{ key: 'bs.cash', page: 2, printed_figure: '100', printed_label: null, row_label: null, reason: 'ambiguous', detail: null, fact_id: 'f-1', reads_as: null }]);
    expect(heldCells({ items: [] })).toEqual([]);
  });

  it('takes the line a label names, and the value under it, only as the API gave them', () => {
    expect(heldCells({ cells: [PAYABLE_ROW] })[0]?.reads_as).toEqual({ key: 'bs.accounts_payable', value: '8067000' });
    expect(heldCells({ cells: [{ ...PAYABLE_ROW, reads_as: { key: 'bs.accounts_payable' } }] })[0]?.reads_as).toBeNull();
    expect(heldCells({ cells: [{ ...PAYABLE_ROW, reads_as: 'bs.accounts_payable' }] })[0]?.reads_as).toBeNull();
  });

  it('reads the period and units of the spread, and the checks that failed', () => {
    expect(spreadContext(item().evidence)).toEqual({ document_id: 'd-1', period_end: '2026-09-30', months: 9, scale: 1000 });
    expect(spreadContext({ note: 'Stand-in', seeded: true })).toBeNull();
    expect(footingProblems({ checks: [{ key: 'bs.total_assets', code: 'does_not_foot', message: 'footing check failed', detail: { actual: '64400000', expected: '64410000', difference: '-10000', tolerance: '4000' } }, { message: 'no code' }] })).toEqual([
      { key: 'bs.total_assets', code: 'does_not_foot', message: 'footing check failed', detail: { actual: '64400000', expected: '64410000', difference: '-10000' } },
    ]);
  });

  it('names a line, and knows which keys a person may enter', () => {
    expect(describeLine('bs.accrued_liabilities', SPREAD.lines)).toEqual({ base: 'bs.accrued_liabilities', label: 'Accrued liabilities', statement: 'Balance sheet', qualifier: null, input: true, flow: false });
    expect(describeLine('stated.bs.total_assets', SPREAD.lines)).toMatchObject({ base: 'bs.total_assets', label: 'Total assets', qualifier: 'printed total', input: false });
    expect(describeLine('is.interest_expense@comparative', SPREAD.lines)).toMatchObject({ base: 'is.interest_expense', qualifier: 'comparative column', input: false });
    expect(describeLine('cf.capex', [])).toMatchObject({ label: 'Capex', statement: 'Cash flow statement', input: true });
  });

  it('counts a line as waiting until a person has cleared it', () => {
    expect(needsPerson('f-ap', fact({ status: 'proposed' }), undefined)).toBe(true);
    expect(needsPerson('f-ap', fact({ status: 'confirmed' }), undefined)).toBe(false);
    expect(needsPerson('f-ap', fact({ status: 'superseded' }), fact({ id: 'f-new', kind: 'manual', status: 'confirmed' }))).toBe(false);
    expect(needsPerson(null, undefined, undefined)).toBe(true);
    expect(needsPerson(null, undefined, fact({ id: 'f-keyed', kind: 'manual', status: 'confirmed' }))).toBe(false);
  });
});

describe('what a held figure needs, decided without the screen', () => {
  const [payable, interest] = heldCells({ cells: [PAYABLE_ROW, INTEREST_ROW] }) as [HeldCell, HeldCell];
  const accrued = describeLine('bs.accrued_liabilities', SPREAD.lines);
  const target = describeLine('bs.accounts_payable', SPREAD.lines);

  it('says why a figure was held in plain words, naming lines as the screen does and never by key', () => {
    expect(whyHeld(payable, accrued, target)).toEqual({ sentence: 'The row is printed “Accounts payable”, which names Accounts payable, not Accrued liabilities, the line it was filed under.', detail: null });
    expect(whyHeld(interest, describeLine('is.interest_expense', SPREAD.lines), null)).toEqual({ sentence: 'The figure the reader reported is not on the page it cited. Nothing was stored.', detail: null });
    const unfamiliar = { ...payable, row_label: 'Trade creditors', detail: "the label 'Trade creditors' is not a known name for 'Accrued liabilities'", reads_as: null };
    expect(whyHeld(unfamiliar, accrued, null).sentence).toBe('The row is printed “Trade creditors”, which is not a name Accrued liabilities is known by.');
    // A reason this screen has no sentence for is still shown, with the check's own words beneath.
    expect(whyHeld({ ...payable, reason: 'column_unconfirmed', detail: 'two columns end 30 Sep', reads_as: null }, accrued, null)).toEqual({
      sentence: 'The figure is on the page, but its column could not be confirmed as the one for this period.',
      detail: 'two columns end 30 Sep',
    });
    expect(whyHeld({ ...payable, reason: 'held_by_new_rule', detail: null, reads_as: null }, accrued, null).sentence).toBe('Held by new rule.');
  });

  it('offers one action first: file where the label says, reject a duplicate, keep as read, or enter what is missing', () => {
    const state = { heldOpen: true, onFile: true, target, targetOnFile: false, inPair: false, canEnter: false };
    expect(primaryAction(state)).toBe('file');
    expect(primaryAction({ ...state, targetOnFile: true })).toBe('reject');
    expect(primaryAction({ ...state, target: null })).toBe('keep');
    // Both figures of a swapped pair share the pair's one action.
    expect(primaryAction({ ...state, inPair: true })).toBeNull();
    expect(primaryAction({ ...state, heldOpen: false, onFile: false, canEnter: true })).toBe('enter');
    expect(primaryAction({ ...state, heldOpen: false, onFile: false, canEnter: false })).toBeNull();
    // A figure a person has already confirmed or replaced asks for nothing more.
    expect(primaryAction({ ...state, heldOpen: false, onFile: true, canEnter: true })).toBeNull();
  });

  it('finds two readings filed under each other’s lines, and only where two corrections can put them right', () => {
    const cells = heldCells({ cells: [INTEREST_ROW, PAYABLE_ROW, ACCRUED_ROW] });
    expect(swappedPairs(cells, SPREAD.lines)).toEqual([[1, 2]]);
    // One label names the other's line but not the reverse: not a swap.
    expect(swappedPairs(heldCells({ cells: [PAYABLE_ROW, { ...ACCRUED_ROW, reads_as: null }] }), SPREAD.lines)).toEqual([]);
    // Nothing stored for one of them: there is no fact to correct.
    expect(swappedPairs(heldCells({ cells: [PAYABLE_ROW, { ...ACCRUED_ROW, fact_id: null }] }), SPREAD.lines)).toEqual([]);
    // Rows on different pages: a correction would cite the page of the figure it replaced.
    expect(swappedPairs(heldCells({ cells: [PAYABLE_ROW, { ...ACCRUED_ROW, page: 3 }] }), SPREAD.lines)).toEqual([]);
    // Comparative-column figures cannot be corrected from here.
    const comparative = [
      { ...PAYABLE_ROW, key: 'bs.accrued_liabilities@comparative', reads_as: { key: 'bs.accounts_payable@comparative', value: '7000000' } },
      { ...ACCRUED_ROW, key: 'bs.accounts_payable@comparative', reads_as: { key: 'bs.accrued_liabilities@comparative', value: '1000000' } },
    ];
    expect(swappedPairs(heldCells({ cells: comparative }), SPREAD.lines)).toEqual([]);
  });

  it('says before the click what code will do, and does not promise a refooting while no totals are on file', () => {
    expect(whatCodeWillDo(true)).toBe('Results calculated from the old figure will be retired, totals refooted and this period’s covenants retested.');
    expect(whatCodeWillDo(false)).toBe('This statement has no totals on file yet: totals will be footed and this period’s covenants tested once the decision below is recorded.');
  });
});

describe('the held-figures panel', () => {
  it('shows three labelled things for each held figure, in order: on file, read from the document, why it was held', async () => {
    mockApi(READS);
    renderHeld(item());
    await screen.findByRole('button', { name: 'File under Accounts payable' });

    const payable = rowOf('bs.accrued_liabilities');
    expect(payable).toHaveAccessibleName('Held figure: Accrued liabilities');
    expect([...payable.querySelectorAll('dt')].map((term) => term.textContent)).toEqual(['On file', 'Read from the document', 'Why it was held', 'What to do']);
    // On file: the line the figure was filed under and the value stored for it, which opens its source.
    expect(text(payable, '[data-on-file]')).toContain('Accrued liabilities');
    expect(within(payable.querySelector('[data-on-file]') as HTMLElement).getByRole('button', { name: /^\$8,067,000, Accrued liabilities, / })).toBeInTheDocument();
    expect(text(payable, '[data-on-file]')).toContain('held: not used in any calculation until a person decides');
    expect(text(payable, '[data-on-file]')).toContain('Balance sheet, at 30 Sep 2026');
    // Read from the document: the label as printed, the figure as printed, and the link that opens the page.
    const read = within(payable.querySelector('[data-read]') as HTMLElement);
    expect(read.getByText('“Accounts payable”')).toBeInTheDocument();
    expect(read.getByText('8,067')).toHaveClass('tnum');
    expect(read.getByText('as printed, in thousands')).toBeInTheDocument();
    expect(read.getByRole('button', { name: 'Open page 2' })).toBeInTheDocument();
    expect(text(payable, '[data-read]')).toContain('Interim financial statements, Q3 2026');
    // Why: the check's reason in plain words; internal keys and the check's raw wording are not shown.
    expect(text(payable, '[data-why]')).toBe('The row is printed “Accounts payable”, which names Accounts payable, not Accrued liabilities, the line it was filed under.');
    expect(payable.textContent).not.toMatch(/bs\.|reads as/);

    const interest = rowOf('is.interest_expense');
    expect(text(interest, '[data-on-file]')).toBe('Interest expenseNothing on fileIncome statement, 9 months to 30 Sep 2026');
    expect(text(interest, '[data-read]')).toContain('No row label could be read');
    expect(text(interest, '[data-read]')).toContain('The reader reported “Interest expense”.');
    expect(text(interest, '[data-why]')).toBe('The figure the reader reported is not on the page it cited. Nothing was stored.');
    expect(screen.getByText('3 of 3 still need a person')).toBeInTheDocument();
    expect(within(payable).getByText('Needs a person')).toBeInTheDocument();
  });

  it('offers exactly one primary action per held figure, named for what it does, with the other choices beside it', async () => {
    mockApi(READS);
    renderHeld(item());
    await screen.findByRole('button', { name: 'File under Accounts payable' });
    const payable = rowOf('bs.accrued_liabilities');
    expect(primaries(payable)).toEqual(['File under Accounts payable']);
    expect(within(payable).getAllByRole('button').map((button) => button.textContent).slice(-3)).toEqual(['Keep as read', 'Enter a different figure', 'Reject this reading']);
    expect(screen.queryByRole('button', { name: /^Confirm|^Correct/ })).toBeNull();
    // Before the click: what it will do, what code will then do, and the reason that will be recorded.
    expect(text(payable, '[data-will-do]')).toBe(
      'Stores this figure under Accounts payable and sets the reading under Accrued liabilities aside, which leaves Accrued liabilities with nothing on file until its own figure is entered. This statement has no totals on file yet: totals will be footed and this period’s covenants tested once the decision below is recorded.',
    );
    expect(within(payable).getByRole('button', { name: 'File under Accounts payable' })).toHaveAccessibleDescription(text(payable, '[data-will-do]'));
    expect(within(payable).getByText(/with this reason: “The row is printed “Accounts payable” on page 2, so the figure is filed under Accounts payable, not Accrued liabilities\.”/)).toBeInTheDocument();

    // Nothing was stored: the one action is to enter the figure.
    const interest = rowOf('is.interest_expense');
    expect(primaries(interest)).toEqual(['Enter the figure']);
    expect(within(interest).queryByRole('button', { name: /Keep|Reject|different/ })).toBeNull();

    // A printed total is calculated by code: nothing is offered, and the row says why.
    const total = rowOf('stated.bs.total_assets');
    expect(primaries(total)).toEqual([]);
    expect(within(total).getByText(/A printed total cannot be entered: totals are calculated by code from their lines/)).toBeInTheDocument();
  });

  it('files a figure under the line its label names as two ordinary calls, with the value the API gave, and shows what each did', async () => {
    const routes: Record<string, Route> = {
      ...READS,
      'POST /api/v1/borrowers/b-1/facts': { status: 201, body: changed({ id: 'f-new', key: 'bs.accounts_payable', label: 'Accounts payable' }, { retired: 3, totals: 'recalculated', metrics: [], covenants: [] }) },
      'POST /api/v1/facts/f-ap/reject': { body: changed({ kind: 'extracted', status: 'rejected' }) },
    };
    const calls = mockApi(routes);
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'File under Accounts payable' }));
    const payable = rowOf('bs.accrued_liabilities');
    await within(payable).findByText('What code recalculated when the reading under Accrued liabilities was set aside');

    const reason = 'The row is printed “Accounts payable” on page 2, so the figure is filed under Accounts payable, not Accrued liabilities.';
    expect(posts(calls)).toEqual([
      { url: '/api/v1/borrowers/b-1/facts', body: { key: 'bs.accounts_payable', period_end: '2026-09-30', months: 9, value: '8067000', reason, read_from_fact_id: 'f-ap' } },
      { url: '/api/v1/facts/f-ap/reject', body: { reason } },
    ]);
    const notes = within(payable).getAllByRole('status');
    expect(notes[0]).toHaveTextContent('What code recalculated when the figure was stored under Accounts payable');
    expect(notes[0]).toHaveTextContent('3 results calculated from this figure were retired.');
    expect(notes[0]).toHaveTextContent('Statement totals were recalculated from the figures now on file, and the statements foot.');
    expect(notes[1]).toHaveTextContent('Nothing had been calculated from this figure, so nothing was retired or recalculated.');
    expect(within(payable).getByText('Stored under Accounts payable. On file there now:')).toBeInTheDocument();
  });

  it('files the value the API worked out for the other line, not the stored value, when the two lines store opposite signs', async () => {
    const outflow = { key: 'cf.other_investing', page: 4, printed_figure: '(1,200)', printed_label: 'Purchases of property and equipment', row_label: 'Purchases of property and equipment', reason: 'mapping_doubt', detail: null, fact_id: 'f-capex', reads_as: { key: 'cf.capex', value: '1200000' } };
    const calls = mockApi({
      ...READS,
      'GET /api/v1/borrowers/b-1/spread': { body: spread({ 'cf.other_investing': heldCell('f-capex', '-1200000') }) },
      'GET /api/v1/ui/facts': { body: { 'f-capex': fact({ id: 'f-capex', key: 'cf.other_investing', label: 'Other investing', value: '-1200000', months: 9 }) } },
      'POST /api/v1/borrowers/b-1/facts': { status: 201, body: changed({ id: 'f-new', key: 'cf.capex', value: '1200000', months: 9 }) },
      'POST /api/v1/facts/f-capex/reject': { body: changed({ id: 'f-capex', status: 'rejected' }) },
    });
    renderHeld(item({}, [outflow]));
    await userEvent.click(await screen.findByRole('button', { name: 'File under Purchases of property and equipment' }));
    await waitFor(() => expect(posts(calls)).toHaveLength(2));
    expect(posts(calls)[0]?.body).toMatchObject({ key: 'cf.capex', months: 9, value: '1200000' });
  });

  it('offers rejection first when the line the label names already has a figure, and shows that figure', async () => {
    const calls = mockApi({
      ...READS,
      'GET /api/v1/borrowers/b-1/spread': { body: spread({ 'bs.accounts_payable': { '2026-09-30': { fact_id: 'f-on-file', value: '8067000', kind: 'extracted', status: 'verified', usable: true } } }) },
      'GET /api/v1/ui/facts': { body: { 'f-ap': fact({}), 'f-on-file': fact({ id: 'f-on-file', key: 'bs.accounts_payable', label: 'Accounts payable', status: 'verified' }) } },
      'POST /api/v1/facts/f-ap/reject': { body: changed({ kind: 'extracted', status: 'rejected' }) },
    });
    renderHeld(item());
    const payable = rowOf('bs.accrued_liabilities') ?? (await waitFor(() => rowOf('bs.accrued_liabilities')));
    await within(payable).findByRole('button', { name: 'Reject this reading of Accrued liabilities' });
    expect(primaries(payable)).toEqual(['Reject this reading']);
    expect(text(payable, '[data-will-do]')).toMatch(/^Accounts payable already has \$8,067,000 on file, so this sets the reading aside and leaves Accrued liabilities with nothing on file/);
    expect(within(payable.querySelector('[data-will-do]') as HTMLElement).getByRole('button', { name: /^\$8,067,000, Accounts payable, / })).toBeInTheDocument();
    await userEvent.click(within(payable).getByRole('button', { name: 'Reject this reading of Accrued liabilities' }));
    await within(payable).findByText('What code recalculated when the reading under Accrued liabilities was set aside');
    expect(posts(calls)).toEqual([{ url: '/api/v1/facts/f-ap/reject', body: { reason: 'The row is printed “Accounts payable” on page 2, which names Accounts payable; Accounts payable already has a figure on file.' } }]);
  });

  it('keeps a figure as read when its label names no other line, and says that confirming recalculates nothing', async () => {
    const unfamiliar = { ...PAYABLE_ROW, row_label: 'Trade creditors', detail: "the label 'Trade creditors' is not a known name for 'Accrued liabilities'", reads_as: null };
    const calls = mockApi({ ...READS, 'POST /api/v1/facts/f-ap/confirm': { body: fact({ status: 'confirmed' }) } });
    renderHeld(item({}, [unfamiliar]));
    const keep = await screen.findByRole('button', { name: 'Keep as read: Accrued liabilities' });
    const row = rowOf('bs.accrued_liabilities');
    expect(primaries(row)).toEqual(['Keep as read']);
    expect(text(row, '[data-will-do]')).toBe(
      'Keeps this figure under Accrued liabilities, confirmed in your name, and accepts “Trade creditors” as a name for that line for this borrower from now on. No value changes, so nothing is recalculated now: totals will be footed once the decision below is recorded.',
    );
    await userEvent.click(keep);
    expect(await within(row).findByText('Kept as read and confirmed in your name. No value changed, so code recalculated nothing.')).toBeInTheDocument();
    expect(posts(calls).map((call) => call.url)).toEqual(['/api/v1/facts/f-ap/confirm']);
  });

  it('shows a refusal beside the control in the server’s words', async () => {
    const unfamiliar = { ...PAYABLE_ROW, row_label: 'Trade creditors', reads_as: null };
    mockApi({ ...READS, 'POST /api/v1/facts/f-ap/confirm': { status: 422, body: { detail: 'a superseded fact cannot be confirmed' } } });
    renderHeld(item({}, [unfamiliar]));
    await userEvent.click(await screen.findByRole('button', { name: 'Keep as read: Accrued liabilities' }));
    const refusal = await within(rowOf('bs.accrued_liabilities')).findByRole('alert');
    expect(refusal).toHaveTextContent('Not kept: the server refused this. The server said: “a superseded fact cannot be confirmed”');
  });

  it('says when two readings look swapped, and files both under the lines their labels name as two corrections', async () => {
    const calls = mockApi({
      ...SWAPPED,
      'POST /api/v1/facts/f-ap/correct': { body: changed({ id: 'f-new-al', value: '1966000' }, { retired: 2, totals: 'recalculated', metrics: [], covenants: [] }) },
      'POST /api/v1/facts/f-al/correct': { body: changed({ id: 'f-new-ap', key: 'bs.accounts_payable', label: 'Accounts payable' }) },
    });
    renderHeld(item({}, [PAYABLE_ROW, ACCRUED_ROW, INTEREST_ROW]));
    const swap = await screen.findByRole('button', { name: 'File both under the lines their labels name' });
    const pair = document.querySelector('[data-swapped-pair]') as HTMLElement;
    expect(pair).toHaveTextContent('Two readings look swapped. The row printed “Accounts payable” was filed under Accrued liabilities, and the row printed “Accrued liabilities” under Accounts payable.');
    expect(text(pair, '[data-will-do]')).toBe(
      'Stores each figure under the line its printed label names, as two corrections in your name. This statement has no totals on file yet: totals will be footed and this period’s covenants tested once the decision below is recorded.',
    );
    // One action for the two figures: neither row has a primary of its own, only the other choices.
    expect(primaries(document.querySelector('[data-held-figures]') as HTMLElement)).toEqual(['File both under the lines their labels name', 'Enter the figure']);
    for (const key of ['bs.accrued_liabilities', 'bs.accounts_payable']) {
      expect(primaries(rowOf(key))).toEqual([]);
      expect(within(rowOf(key)).getAllByRole('button').map((button) => button.textContent).slice(-3)).toEqual(['Keep as read', 'Enter a different figure', 'Reject this reading']);
    }

    await userEvent.click(swap);
    expect(await within(pair).findByText('Both filed under the lines their labels name')).toBeInTheDocument();
    const reason =
      'Two readings on page 2 were filed under each other’s lines. The row printed “Accounts payable” was filed under Accrued liabilities, and the row printed “Accrued liabilities” under Accounts payable. Each figure is now filed under the line its printed label names.';
    // Each line takes the value the API gave for the figure whose label names it.
    expect(posts(calls)).toEqual([
      { url: '/api/v1/facts/f-ap/correct', body: { value: '1966000', reason } },
      { url: '/api/v1/facts/f-al/correct', body: { value: '8067000', reason } },
    ]);
    const notes = within(pair).getAllByRole('status').filter((note) => note.hasAttribute('data-recalculation'));
    expect(notes[0]).toHaveTextContent('What code recalculated when Accrued liabilities was corrected');
    expect(notes[0]).toHaveTextContent('2 results calculated from the old figure were retired.');
    expect(notes[1]).toHaveTextContent('What code recalculated when Accounts payable was corrected');
    expect(notes[1]).toHaveTextContent('Nothing had been calculated from the old figure, so nothing was retired or recalculated.');
    expect(within(pair).queryByRole('button', { name: 'File both under the lines their labels name' })).toBeNull();
  });

  it('says which of the two corrections was refused, in the server’s words, and offers the pair’s action no further', async () => {
    mockApi({
      ...SWAPPED,
      'POST /api/v1/facts/f-ap/correct': { body: changed({ id: 'f-new-al', value: '1966000' }) },
      'POST /api/v1/facts/f-al/correct': { status: 422, body: { detail: 'a rejected figure cannot be corrected' } },
    });
    renderHeld(item({}, [PAYABLE_ROW, ACCRUED_ROW]));
    await userEvent.click(await screen.findByRole('button', { name: 'File both under the lines their labels name' }));
    const pair = document.querySelector('[data-swapped-pair]') as HTMLElement;
    expect(await within(pair).findByRole('alert')).toHaveTextContent('Accrued liabilities was corrected, but Accounts payable was not: the server refused this. The server said: “a rejected figure cannot be corrected”');
    expect(within(pair).queryByRole('button', { name: 'File both under the lines their labels name' })).toBeNull();
    expect(within(pair).queryByText('Both filed under the lines their labels name')).toBeNull();
  });

  it('opens the page from the printed figure and from the page link: the stored fact, or the cited page when nothing was stored', async () => {
    mockApi(READS);
    const open = vi.fn();
    renderHeld(item(), analyst, open);
    await screen.findByRole('button', { name: 'File under Accounts payable' });
    await userEvent.click(screen.getByRole('button', { name: '8,067, Accrued liabilities as printed on page 2. Read from a document. Show source.' }));
    expect(open).toHaveBeenLastCalledWith({ type: 'fact', id: 'f-ap' });
    await userEvent.click(within(rowOf('bs.accrued_liabilities')).getByRole('button', { name: 'Open page 2' }));
    expect(open).toHaveBeenCalledTimes(2);
    expect(open).toHaveBeenLastCalledWith({ type: 'fact', id: 'f-ap' });
    await userEvent.click(screen.getByRole('button', { name: '1,236, Interest expense as printed on page 3. Read from a document. Show source.' }));
    expect(open).toHaveBeenLastCalledWith({ type: 'document', documentId: 'd-1', page: 3, quote: '1,236', title: 'Interim financial statements, Q3 2026', borrowerCode: 'harrowgate-precision' });
  });

  it('shows no repair control to a role without the permission, and says who has it', async () => {
    mockApi(SWAPPED);
    renderHeld(item({}, [PAYABLE_ROW, ACCRUED_ROW, INTEREST_ROW]), officer);
    await waitFor(() => expect(screen.getByText('3 of 3 still need a person')).toBeInTheDocument());
    // The finding is still said; the action is not offered.
    expect(await screen.findByText('Two readings look swapped.')).toBeInTheDocument();
    expect(document.querySelectorAll('[data-primary], [data-actions], [data-will-do]')).toHaveLength(0);
    expect(screen.getByText(/needs a credit analyst\. Your role, Credit officer, can read the held figures and open their pages\./)).toBeInTheDocument();
  });

  it('asks for a value and a reason before a different figure is sent, then says what was recalculated', async () => {
    const calls = mockApi({ ...READS, 'POST /api/v1/facts/f-ap/correct': { body: changed({ id: 'f-new', value: '1966000' }, { retired: 4, totals: 'does_not_foot', metrics: [], covenants: [] }) } });
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'Enter a different figure for Accrued liabilities' }));
    const form = screen.getByRole('form', { name: 'Enter a different figure for Accrued liabilities' });
    const value = within(form).getByLabelText('Value, in whole US dollars');
    expect(value).toHaveValue('8067000');
    expect(value).toHaveFocus();
    expect(within(form).getByText('Will be stored as $8,067,000, shown on a statement in thousands as 8,067.')).toBeInTheDocument();

    await userEvent.clear(value);
    await userEvent.type(value, '1.9m');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the figure' }));
    expect(value).toHaveAccessibleDescription('This is not a number. Enter digits only, for example 1236000.');
    expect(value).toBeInvalid();
    expect(within(form).getByLabelText('Reason (required)')).toHaveAccessibleDescription('A reason is required. It is recorded in the ledger with your name.');
    expect(calls.some((call) => call.method === 'POST')).toBe(false);

    await userEvent.clear(value);
    await userEvent.type(value, '1,966,000');
    await userEvent.type(within(form).getByLabelText('Reason (required)'), 'Row reads accrued liabilities on page 2.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the figure' }));

    const note = await within(rowOf('bs.accrued_liabilities')).findByRole('status');
    expect(note).toHaveTextContent('What code recalculated');
    expect(note).toHaveTextContent('4 results calculated from the old figure were retired.');
    expect(note).toHaveTextContent('The statements no longer foot, so no totals are stored.');
    expect(posts(calls)).toEqual([{ url: '/api/v1/facts/f-ap/correct', body: { value: '1966000', reason: 'Row reads accrued liabilities on page 2.' } }]);
    expect(screen.queryByRole('form', { name: 'Enter a different figure for Accrued liabilities' })).toBeNull();
  });

  it('rejects a reading only with a reason, and says the line then has no figure', async () => {
    const calls = mockApi({ ...READS, 'POST /api/v1/facts/f-ap/reject': { body: changed({ kind: 'extracted', status: 'rejected' }) } });
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'Reject this reading of Accrued liabilities' }));
    const form = screen.getByRole('form', { name: 'Reject this reading of Accrued liabilities' });
    expect(within(form).queryByLabelText('Value, in whole US dollars')).toBeNull();
    expect(within(form).getByLabelText('Reason (required)')).toHaveAccessibleDescription('Recorded in the ledger with your name. Accrued liabilities then has no figure until one is entered.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the rejection' }));
    expect(calls.some((call) => call.method === 'POST')).toBe(false);
    await userEvent.type(within(form).getByLabelText('Reason (required)'), 'The row is not on this statement.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the rejection' }));
    await within(rowOf('bs.accrued_liabilities')).findByText('Nothing had been calculated from this figure, so nothing was retired or recalculated.');
    expect(posts(calls)).toEqual([{ url: '/api/v1/facts/f-ap/reject', body: { reason: 'The row is not on this statement.' } }]);
  });

  it('enters a figure for the line and period the spread was read for', async () => {
    const calls = mockApi({ ...READS, 'POST /api/v1/borrowers/b-1/facts': { status: 201, body: changed({ id: 'f-keyed', key: 'is.interest_expense', value: '1235000', months: 9 }) } });
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'Enter the figure for Interest expense' }));
    const form = screen.getByRole('form', { name: 'Enter Interest expense, 9 months to 30 Sep 2026' });
    await userEvent.type(within(form).getByLabelText('Value, in whole US dollars'), '1235000');
    await userEvent.type(within(form).getByLabelText('Reason (required)'), 'Read from page 3 by hand.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the figure' }));
    await screen.findByText('Nothing had been calculated from this figure, so nothing was retired or recalculated.');
    expect(posts(calls)).toEqual([{ url: '/api/v1/borrowers/b-1/facts', body: { key: 'is.interest_expense', period_end: '2026-09-30', months: 9, value: '1235000', reason: 'Read from page 3 by hand.' } }]);
  });

  it('promises a refooting before the click only when the statement’s totals are on file', async () => {
    mockApi({ ...READS, 'GET /api/v1/borrowers/b-1/spread': { body: spread({ 'bs.total_assets': { '2026-09-30': { fact_id: 'f-total', value: '64410000', kind: 'calculated', status: 'verified', usable: true } } }) } });
    renderHeld(item());
    await screen.findByRole('button', { name: 'File under Accounts payable' });
    expect(text(rowOf('bs.accrued_liabilities'), '[data-will-do]')).toMatch(/Results calculated from the old figure will be retired, totals refooted and this period’s covenants retested\.$/);
  });

  it('lists the failed checks of a spread that does not foot, with the amounts compared as figures that open their source', async () => {
    mockApi(READS);
    const open = vi.fn();
    renderHeld(
      item({
        item_type: 'spread.does_not_foot',
        evidence: {
          document_id: 'd-1',
          spread: { document_id: 'd-1', period_end: '2026-09-30', months: 9, scale: 1000 },
          checks: [
            { key: 'bs.total_assets', code: 'does_not_foot', message: 'footing check failed for bs.total_assets: 64400000 against 64410000', detail: { actual: '64400000', expected: '64410000', difference: '-10000' } },
            { key: 'bs.accounts_payable', code: 'missing_input', message: 'missing input bs.accounts_payable', detail: {} },
          ],
        },
      }),
      analyst,
      open,
    );
    const total = within(await waitFor(() => document.querySelector('[data-check-row="bs.total_assets"]') as HTMLElement));
    expect(total.getByText('The lines do not add to the printed total')).toBeInTheDocument();
    // The raw message carries typed figures; the amounts are shown as figures instead.
    expect(screen.queryByText(/64400000 against 64410000/)).toBeNull();
    await userEvent.click(total.getByRole('button', { name: /\$64,400,000, Lines add to, Total assets/ }));
    expect(open).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'record', kind: 'calculated', value: '$64,400,000', rows: [['Lines add to', '$64,400,000'], ['Printed total', '$64,410,000'], ['Difference', '($10,000)']] }));

    const payable = within(document.querySelector('[data-check-row="bs.accounts_payable"]') as HTMLElement);
    expect(payable.getByText('No figure is on file for this line')).toBeInTheDocument();
    // A balance is entered for the period end, not for the months of the period.
    await userEvent.click(payable.getByRole('button', { name: 'Enter the figure for Accounts payable' }));
    expect(screen.getByRole('form', { name: 'Enter Accounts payable, at 30 Sep 2026' })).toBeInTheDocument();

    // Any other input line can be entered or replaced; the picker starts on the first line a check named.
    await userEvent.click(screen.getByRole('button', { name: 'Enter a figure for another line' }));
    expect(screen.getByRole('combobox', { name: 'Line of the statement, period ended 30 Sep 2026' })).toHaveTextContent('Balance sheet · Accounts payable');
  });
});

describe('the recalculation note', () => {
  it('is announced, and marks a changed covenant outcome where the breach is named', async () => {
    mockApi({ 'GET /api/v1/ui/borrowers/b-1/covenants': { body: { tests: [{ covenant_id: 'total_leverage', covenant_name: 'Total Leverage Ratio' }], facts: {} } } });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <RecalculationNote
          borrowerId="b-1"
          recalculation={{ retired: 5, totals: 'recalculated', metrics: [], covenants: [{ facility_id: 'l-1', period_end: '2026-09-30', covenant_id: 'total_leverage', before: 'compliant', after: 'breach' }] }}
        />
      </QueryClientProvider>,
    );
    const note = screen.getByRole('status');
    expect(note).toHaveAttribute('aria-live', 'polite');
    const change = await within(note).findByRole('listitem', { name: 'Total Leverage Ratio, Q3 2026: Compliant → Breach' });
    expect(within(change).getByText('Breach')).toHaveClass('text-red');
    expect(within(change).getByText('Compliant')).not.toHaveClass('text-red');
  });
});
