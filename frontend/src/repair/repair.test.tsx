import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser, FactSummary, Recalculation, Spread, WorkItemDetail } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { describeLine, footingProblems, heldCells, HeldFigures, needsPerson, spreadContext } from '@/screens/work/HeldFigures';
import { SourceContext, type SourceRef } from '@/source/context';
import { parseFigureInput, readBack } from './FigureForm';
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

/* ── The held-figure table ────────────────────────────────────────────── */

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

const item = (over: Partial<WorkItemDetail> = {}): WorkItemDetail => ({
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
  evidence: {
    document_id: 'd-1',
    spread: { document_id: 'd-1', period_end: '2026-09-30', months: 9, scale: 1000, absent: [] },
    cells: [
      { key: 'bs.accrued_liabilities', page: 2, printed_figure: '8,067', printed_label: 'Accounts payable', row_label: 'Accounts payable', reason: 'mapping_doubt', detail: "the label 'Accounts payable' reads as bs.accounts_payable, not bs.accrued_liabilities", fact_id: 'f-ap' },
      { key: 'is.interest_expense', page: 3, printed_figure: '1,236', printed_label: 'Interest expense', row_label: '', reason: 'not_found', detail: "'1,236' is not on the cited page", fact_id: null },
      { key: 'stated.bs.total_assets', page: 2, printed_figure: '64,410', printed_label: 'Total assets', row_label: '', reason: 'not_found', detail: null, fact_id: null },
    ],
  },
  ...over,
});

const SPREAD: Spread = {
  template: 'standard',
  periods: [{ period_end: '2026-09-30', months: 9 }],
  lines: [
    { key: 'is.interest_expense', label: 'Interest expense', statement: 'is', computed: false, cells: {} },
    { key: 'bs.accounts_payable', label: 'Accounts payable', statement: 'bs', computed: false, cells: {} },
    { key: 'bs.accrued_liabilities', label: 'Accrued liabilities', statement: 'bs', computed: false, cells: { '2026-09-30': { fact_id: 'f-ap', value: '8067000', kind: 'extracted', status: 'proposed', usable: false } } },
    { key: 'bs.total_assets', label: 'Total assets', statement: 'bs', computed: true, cells: {} },
  ],
};

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

afterEach(() => vi.unstubAllGlobals());

describe('reading a held spread’s evidence', () => {
  it('lists the held cells and leaves out anything malformed', () => {
    const cells = heldCells({ cells: [{ key: 'bs.cash', page: 2, printed_figure: '100', reason: 'ambiguous', fact_id: 'f-1' }, { page: 2 }, 'nonsense', null] });
    expect(cells).toEqual([{ key: 'bs.cash', page: 2, printed_figure: '100', printed_label: null, row_label: null, reason: 'ambiguous', detail: null, fact_id: 'f-1' }]);
    expect(heldCells({ items: [] })).toEqual([]);
  });

  it('reads the period and units of the spread, and the checks that failed', () => {
    expect(spreadContext(item().evidence)).toEqual({ document_id: 'd-1', period_end: '2026-09-30', months: 9, scale: 1000 });
    expect(spreadContext({ note: 'Stand-in', seeded: true })).toBeNull();
    expect(footingProblems({ checks: [{ key: 'bs.total_assets', code: 'does_not_foot', message: 'footing check failed', detail: { actual: '64400000', expected: '64410000', difference: '-10000', tolerance: '4000' } }, { message: 'no code' }] })).toEqual([
      { key: 'bs.total_assets', code: 'does_not_foot', message: 'footing check failed', detail: { actual: '64400000', expected: '64410000', difference: '-10000' } },
    ]);
  });

  it('names a line, and knows which keys a person may key', () => {
    expect(describeLine('bs.accrued_liabilities', SPREAD.lines)).toEqual({ base: 'bs.accrued_liabilities', label: 'Accrued liabilities', statement: 'Balance sheet', qualifier: null, input: true });
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

describe('the held-figure table', () => {
  it('shows each held figure with its line, the row label read from the page, the printed figure and why it was held', async () => {
    mockApi(READS);
    renderHeld(item());
    const table = await screen.findByRole('table');
    expect(within(table).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual(['Line', 'Row label on the page', 'Printed']);
    await screen.findByRole('button', { name: 'Confirm Accrued liabilities as read' });

    const payable = rowOf('bs.accrued_liabilities');
    expect(within(payable).getByRole('rowheader')).toHaveTextContent('Accrued liabilitiesBalance sheet');
    expect(within(payable).getByText('Accounts payable')).toBeInTheDocument();
    expect(within(payable).getByText('8,067')).toHaveClass('tnum');
    expect(within(payable).getByText('page 2')).toBeInTheDocument();
    expect(within(payable).getByText('Held: the row label is not a known name for this line')).toBeInTheDocument();
    expect(within(payable).getByText("the label 'Accounts payable' reads as bs.accounts_payable, not bs.accrued_liabilities")).toBeInTheDocument();

    const interest = rowOf('is.interest_expense');
    expect(within(interest).getByRole('rowheader')).toHaveTextContent('Interest expenseIncome statement');
    expect(within(interest).getByText('No label read')).toBeInTheDocument();
    expect(within(interest).getByText('The reader reported “Interest expense”')).toBeInTheDocument();
    expect(within(interest).getByText('Held: the figure was not found on the page')).toBeInTheDocument();
    expect(screen.getByText('3 of 3 still need a person')).toBeInTheDocument();
  });

  it('offers Confirm and Correct only for a figure that was stored, and Key a figure only where nothing was', async () => {
    mockApi(READS);
    renderHeld(item());
    await screen.findByRole('button', { name: 'Confirm Accrued liabilities as read' });
    const payable = within(rowOf('bs.accrued_liabilities'));
    expect(payable.getByRole('button', { name: 'Correct Accrued liabilities' })).toBeInTheDocument();
    expect(payable.queryByRole('button', { name: /Key a figure/ })).toBeNull();

    const interest = within(rowOf('is.interest_expense'));
    expect(interest.getByRole('button', { name: 'Key a figure for Interest expense' })).toBeInTheDocument();
    expect(interest.queryByRole('button', { name: /Confirm|Correct/ })).toBeNull();

    // A printed total is calculated by code: it can be neither confirmed nor keyed, and the row says why.
    const total = within(rowOf('stated.bs.total_assets'));
    expect(total.queryByRole('button', { name: /Confirm|Correct|Key/ })).toBeNull();
    expect(total.getByText(/A printed total cannot be keyed: totals are calculated by code from their lines/)).toBeInTheDocument();
  });

  it('opens the source drawer from each printed figure: the stored fact, or the cited page when nothing was stored', async () => {
    mockApi(READS);
    const open = vi.fn();
    renderHeld(item(), analyst, open);
    await screen.findByRole('button', { name: 'Confirm Accrued liabilities as read' });
    await userEvent.click(screen.getByRole('button', { name: '8,067, Accrued liabilities as printed on page 2. Read from a document. Show source.' }));
    expect(open).toHaveBeenLastCalledWith({ type: 'fact', id: 'f-ap' });
    await userEvent.click(screen.getByRole('button', { name: '1,236, Interest expense as printed on page 3. Read from a document. Show source.' }));
    expect(open).toHaveBeenLastCalledWith({ type: 'document', documentId: 'd-1', page: 3, quote: '1,236', title: 'Interim financial statements, Q3 2026', borrowerCode: 'harrowgate-precision' });
  });

  it('shows no repair control to a role without the permission, and says who has it', async () => {
    mockApi(READS);
    renderHeld(item(), officer);
    await screen.findAllByText('Held: the figure was not found on the page');
    await waitFor(() => expect(screen.getByText('3 of 3 still need a person')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /Confirm|Correct|Key a figure/ })).toBeNull();
    expect(screen.getByText(/needs a credit analyst\. Your role, Credit officer, can read the held figures/)).toBeInTheDocument();
  });

  it('confirms a figure through the API and shows a refusal beside the control in the server’s words', async () => {
    const calls = mockApi({ ...READS, 'POST /api/v1/facts/f-ap/confirm': { status: 422, body: { detail: 'a superseded fact cannot be confirmed' } } });
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'Confirm Accrued liabilities as read' }));
    const refusal = await within(rowOf('bs.accrued_liabilities')).findByRole('alert');
    expect(refusal).toHaveTextContent('Not recorded: the server refused this. The server said: “a superseded fact cannot be confirmed”');
    expect(calls.filter((call) => call.method === 'POST').map((call) => call.url)).toEqual(['/api/v1/facts/f-ap/confirm']);
  });

  it('asks for a value and a reason before a correction is sent, then says what was recalculated', async () => {
    const calls = mockApi({
      ...READS,
      'POST /api/v1/facts/f-ap/correct': {
        body: { ...fact({ id: 'f-new', kind: 'manual', status: 'confirmed', value: '1966000' }), recalculation: { retired: 4, totals: 'does_not_foot', metrics: [], covenants: [] } },
      },
    });
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'Correct Accrued liabilities' }));
    const form = screen.getByRole('form', { name: 'Correct Accrued liabilities' });
    const value = within(form).getByLabelText('Value, in whole US dollars');
    expect(value).toHaveValue('8067000');
    expect(value).toHaveFocus();
    expect(within(form).getByText('Will be stored as $8,067,000, shown on a statement in thousands as 8,067.')).toBeInTheDocument();

    await userEvent.clear(value);
    await userEvent.type(value, '1.9m');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the correction' }));
    expect(value).toHaveAccessibleDescription('This is not a number. Enter digits only, for example 1236000.');
    expect(value).toBeInvalid();
    expect(within(form).getByLabelText('Reason (required)')).toHaveAccessibleDescription('A reason is required. It is recorded in the ledger with your name.');
    expect(calls.some((call) => call.method === 'POST')).toBe(false);

    await userEvent.clear(value);
    await userEvent.type(value, '1,966,000');
    await userEvent.type(within(form).getByLabelText('Reason (required)'), 'Row reads accrued liabilities on page 2.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the correction' }));

    const note = await screen.findByRole('status');
    expect(note).toHaveTextContent('What code recalculated');
    expect(note).toHaveTextContent('4 results calculated from the old figure were retired.');
    expect(note).toHaveTextContent('The statements no longer foot, so no totals are stored.');
    expect(calls.find((call) => call.method === 'POST')).toEqual({ method: 'POST', url: '/api/v1/facts/f-ap/correct', body: { value: '1966000', reason: 'Row reads accrued liabilities on page 2.' } });
    expect(screen.queryByRole('form', { name: 'Correct Accrued liabilities' })).toBeNull();
  });

  it('keys a figure for the line and period the spread was read for', async () => {
    const calls = mockApi({
      ...READS,
      'POST /api/v1/borrowers/b-1/facts': { status: 201, body: { ...fact({ id: 'f-keyed', key: 'is.interest_expense', kind: 'manual', status: 'confirmed', value: '1235000', months: 9 }), recalculation: NOTHING } },
    });
    renderHeld(item());
    await userEvent.click(await screen.findByRole('button', { name: 'Key a figure for Interest expense' }));
    const form = screen.getByRole('form', { name: 'Key Interest expense, 9 months to 30 sep 2026' });
    await userEvent.type(within(form).getByLabelText('Value, in whole US dollars'), '1235000');
    await userEvent.type(within(form).getByLabelText('Reason (required)'), 'Read from page 3 by hand.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the figure' }));
    await screen.findByText('Nothing had been calculated from the old figure, so nothing was retired or recalculated.');
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({ key: 'is.interest_expense', period_end: '2026-09-30', months: 9, value: '1235000', reason: 'Read from page 3 by hand.' });
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
    expect(payable.getByRole('button', { name: 'Key a figure for Accounts payable' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Correct or key another line' })).toBeInTheDocument();
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
