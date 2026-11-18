import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, Outlet, RouterProvider } from '@tanstack/react-router';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BorrowerCovenants, BorrowerOverview, BorrowerRow, CalendarResponse, CovenantTestRow, FactSummary, Obligation, PortfolioSummary, WorkItemRow } from '@/api/schema';
import { BorrowerTearSheet } from '@/drawer/BorrowerTearSheet';
import { useWorkspaceDrawer, WorkspaceDrawerProvider } from '@/drawer/context';
import { SourceContext, type SourceRef } from '@/source/context';
import { Calendar } from './Calendar';
import { Borrowers, Portfolio } from './Portfolio';

/* ── What the API returns ─────────────────────────────────────────────── */

const fact = (over: Partial<FactSummary>): FactSummary => ({
  id: 'f-1',
  key: 'sys.revolver_outstanding',
  label: 'Line of credit, outstanding',
  value: '10989000',
  unit: 'usd',
  kind: 'system',
  status: 'verified',
  period_end: '2026-10-31',
  months: 0,
  borrower_id: 'b-kestrel',
  document_id: null,
  page: null,
  calc_run_id: null,
  ...over,
});

const headroom = (id: string, value: string, covenant: string, borrower: string): FactSummary =>
  fact({ id, key: `cov.${covenant.toLowerCase().replace(/ /g, '_')}.headroom_pct`, label: `${covenant}, headroom`, value, unit: 'pct', kind: 'calculated', period_end: '2026-09-30', borrower_id: borrower, calc_run_id: `calc-${id}` });

const borrower = (over: Partial<BorrowerRow>): BorrowerRow => ({
  id: 'b-kestrel',
  code: 'kestrel-bay-packaging',
  name: 'Kestrel Bay Packaging Corp.',
  industry: 'manufacturing',
  risk_rating: 6,
  fiscal_year_end_month: 12,
  relationship_manager: 'Dana Whitcombe',
  analyst: 'Theo Lindqvist',
  total_commitment: '53555000',
  open_work_items: 1,
  open_signals: 7,
  latest_cycle: { id: 'c-kestrel', period_end: '2026-09-30', stage: 'covenant_testing', status: 'open' },
  covenant_status: 'breach_reported_compliant',
  tightest_headroom: headroom('h-kestrel-leverage', '-0.04', 'Total Leverage Ratio', 'b-kestrel'),
  ...over,
});

const BOOK: BorrowerRow[] = [
  borrower({}),
  borrower({
    id: 'b-quill',
    code: 'quillfeather-bakery',
    name: 'Quillfeather Bakery Brands, Inc.',
    industry: 'food processing',
    risk_rating: 5,
    open_work_items: 0,
    open_signals: 1,
    covenant_status: 'compliant_variance',
    latest_cycle: { id: 'c-quill', period_end: '2026-09-30', stage: 'review_prep', status: 'open' },
    tightest_headroom: headroom('h-quill-fccr', '0.2609', 'Fixed Charge Coverage Ratio', 'b-quill'),
  }),
  borrower({
    id: 'b-sable',
    code: 'sablewood-dental',
    name: 'Sablewood Dental Management, LLC',
    industry: 'healthcare services',
    risk_rating: 4,
    open_work_items: 0,
    open_signals: 0,
    covenant_status: 'compliant',
    latest_cycle: { id: 'c-sable', period_end: '2026-09-30', stage: 'review_prep', status: 'open' },
    tightest_headroom: headroom('h-sable-leverage', '0.492', 'Total Leverage Ratio', 'b-sable'),
  }),
  borrower({
    id: 'b-ash',
    code: 'ashgrove-fleet',
    name: 'Ashgrove Fleet Maintenance, LLC',
    industry: 'services',
    risk_rating: 5,
    open_signals: 0,
    covenant_status: null,
    latest_cycle: { id: 'c-ash', period_end: '2026-09-30', stage: 'spreading', status: 'open' },
    tightest_headroom: null,
  }),
];

const SUMMARY: PortfolioSummary = {
  as_of: '2026-11-17',
  borrowers: 4,
  loans: 7,
  period_end: '2026-09-30',
  exposure: { commitment: '573531500', revolver_outstanding: '128414000', term_loan_outstanding: '225429375', outstanding: '353843375' },
  borrower_exposure: {
    'b-kestrel': {
      revolver_outstanding: fact({ id: 'f-kestrel-line' }),
      commitment: fact({ id: 'f-kestrel-commitment', key: 'sys.commitment', label: 'Line of credit, commitment', value: '15500000' }),
      term_loan_outstanding: fact({ id: 'f-kestrel-term', key: 'sys.term_loan_outstanding', label: 'Term loan, outstanding', value: '22125000' }),
    },
  },
  cycles: { open: 4, by_stage: [{ stage: 'review_prep', count: 2 }] },
  covenants: {
    tests: 46,
    by_outcome: [
      { outcome: 'compliant', count: 39 },
      { outcome: 'breach_reported_compliant', count: 3 },
      { outcome: 'compliant_variance', count: 3 },
      { outcome: 'breach', count: 1 },
    ],
  },
  work_items: {
    open: 13,
    by_type: [],
    by_severity: [
      { severity: 'high', count: 8 },
      { severity: 'critical', count: 4 },
      { severity: 'medium', count: 1 },
    ],
  },
  signals: {
    open: 73,
    by_severity: [
      { severity: 'low', count: 39 },
      { severity: 'medium', count: 32 },
      { severity: 'high', count: 2 },
    ],
  },
  obligations: { overdue: 2, due_within_7_days: 8, received_in_last_30_days: 40 },
};

const OVERVIEW: BorrowerOverview = {
  exposure: { ...SUMMARY.borrower_exposure['b-kestrel'], availability: fact({ id: 'f-kestrel-availability', key: 'bb.availability', label: 'Availability', value: '4511000', kind: 'calculated', period_end: '2026-09-30', calc_run_id: 'calc-bb' }) },
  cycle: {
    id: 'c-kestrel',
    borrower_id: 'b-kestrel',
    period_end: '2026-09-30',
    months: 9,
    cycle_type: 'quarterly',
    stage: 'covenant_testing',
    status: 'open',
    origin: 'seeded',
    due_date: null,
    stages: [
      { id: 's-1', stage: 'spreading', position: 2, status: 'done', detail: {}, open_work_items: 0 },
      { id: 's-2', stage: 'covenant_testing', position: 3, status: 'needs_person', detail: {}, open_work_items: 1 },
      { id: 's-3', stage: 'borrowing_base', position: 4, status: 'pending', detail: {}, open_work_items: 0 },
    ],
  },
  metrics: {},
  open_work_items: 1,
  open_signals: 7,
  documents: 18,
};

const covenantTest = (over: Partial<CovenantTestRow>): CovenantTestRow => ({
  id: 't-leverage',
  borrower_id: 'b-kestrel',
  facility_id: 'fac-1',
  cycle_id: 'c-kestrel',
  covenant_id: 'total_leverage',
  covenant_name: 'Total Leverage Ratio',
  period_end: '2026-09-30',
  calc_run_id: 'calc-1',
  value_fact_id: 'v-leverage',
  threshold_fact_id: 'th-leverage',
  headroom_fact_id: 'h-kestrel-leverage',
  reported_fact_id: null,
  value: '2.6',
  threshold: '2.5',
  operator: '<=',
  unit: 'ratio',
  passed: false,
  reported_value: '2.41',
  reported_in_compliance: true,
  outcome: 'breach_reported_compliant',
  error: null,
  loan_name: 'Revolving line of credit',
  terms_version: null,
  citation: null,
  work_item: { id: 'w-mismatch', item_type: 'covenant.reported_mismatch', status: 'open', severity: 'critical', decision: null, title: 'Total Leverage Ratio fails' },
  ...over,
});

const ratio = (id: string, label: string, value: string): FactSummary => fact({ id, key: `cov.${id}`, label, value, unit: 'ratio', kind: 'calculated', period_end: '2026-09-30', calc_run_id: `calc-${id}` });

const COVENANTS: BorrowerCovenants = {
  tests: [
    covenantTest({}),
    covenantTest({ id: 't-current', covenant_id: 'current_ratio', covenant_name: 'Current Ratio', value_fact_id: 'v-current', threshold_fact_id: 'th-current', headroom_fact_id: 'h-kestrel-current', operator: '>=', outcome: 'compliant', work_item: null }),
    // an earlier period: not part of the sheet
    covenantTest({ id: 't-old', period_end: '2026-06-30', covenant_name: 'Total Leverage Ratio', value_fact_id: 'v-old', threshold_fact_id: 'th-leverage', headroom_fact_id: 'h-old', outcome: 'compliant', work_item: null }),
  ],
  facts: {
    'v-leverage': ratio('v-leverage', 'Total Leverage Ratio', '2.6'),
    'th-leverage': ratio('th-leverage', 'Total Leverage Ratio, threshold in force', '2.5'),
    'h-kestrel-leverage': BOOK[0]!.tightest_headroom!,
    'v-current': ratio('v-current', 'Current Ratio', '1.34'),
    'th-current': ratio('th-current', 'Current Ratio, threshold in force', '1.25'),
    'h-kestrel-current': headroom('h-kestrel-current', '0.072', 'Current Ratio', 'b-kestrel'),
    'v-old': ratio('v-old', 'Total Leverage Ratio', '2.04'),
    'h-old': headroom('h-old', '0.184', 'Total Leverage Ratio', 'b-kestrel'),
  },
};

const ITEMS: WorkItemRow[] = [
  {
    id: 'w-mismatch',
    borrower_id: 'b-kestrel',
    borrower_name: 'Kestrel Bay Packaging Corp.',
    facility_id: null,
    cycle_id: 'c-kestrel',
    stage: 'covenant_testing',
    item_type: 'covenant.reported_mismatch',
    severity: 'critical',
    title: 'Kestrel Bay Packaging Corp.: Total Leverage Ratio fails but the certificate reports compliance',
    question: 'What is the response?',
    allowed_decisions: ['reservation_of_rights'],
    blocks_stage: true,
    requires_second_person: false,
    required_permission: 'decide_breach',
    prepared_by_id: null,
    due_date: '2026-11-24',
    status: 'open',
    decision: null,
    decision_reason: null,
    decided_by: null,
    decided_at: null,
    agent_run_id: null,
    created_at: '2026-11-17T08:00:00+00:00',
  },
];

const obligation = (over: Partial<Obligation>): Obligation => ({
  id: 'o-1',
  borrower_id: 'b-kestrel',
  borrower_name: 'Kestrel Bay Packaging Corp.',
  facility_id: 'fac-1',
  requirement_id: 'r-1',
  document_type: 'compliance_certificate',
  period_end: '2026-09-30',
  due_date: '2026-10-30',
  status: 'overdue',
  received_document_id: null,
  received_date: null,
  days_late: 18,
  ...over,
});

const CALENDAR: CalendarResponse = {
  as_of: '2026-11-17',
  obligations: [
    obligation({}),
    obligation({ id: 'o-2', borrower_id: 'b-sable', borrower_name: 'Sablewood Dental Management, LLC', document_type: 'interim_statements', status: 'received', received_document_id: 'd-9', received_date: '2026-10-28', days_late: null }),
    obligation({ id: 'o-3', borrower_id: 'b-quill', borrower_name: 'Quillfeather Bakery Brands, Inc.', document_type: 'borrowing_base_certificate', period_end: '2026-10-31', due_date: '2026-11-20', status: 'due', days_late: null }),
    obligation({ id: 'o-4', borrower_id: 'b-ash', borrower_name: 'Ashgrove Fleet Maintenance, LLC', period_end: '2025-06-30', due_date: '2025-07-30', status: 'untracked', days_late: null }),
  ],
};

/* ── Harness ──────────────────────────────────────────────────────────── */

function mockApi() {
  const routes: Array<[string, unknown]> = [
    ['/api/v1/ui/portfolio', SUMMARY],
    ['/api/v1/ui/borrowers/b-kestrel/overview', OVERVIEW],
    ['/api/v1/ui/borrowers/b-kestrel/covenants', COVENANTS],
    ['/api/v1/work-items', ITEMS],
    ['/api/v1/calendar', CALENDAR],
    ['/api/v1/borrowers', BOOK],
  ];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const hit = routes.find(([path]) => url.startsWith(path));
      return { ok: Boolean(hit), status: hit ? 200 : 404, text: async () => JSON.stringify(hit ? hit[1] : { detail: 'Not found' }) } as Response;
    }),
  );
}

/** Stands in for the workspace drawer: the tear-sheet when a borrower is chosen, and the drawer's state as text. */
function DrawerStandIn() {
  const drawer = useWorkspaceDrawer();
  return (
    <aside aria-label="Drawer">
      <output data-testid="drawer">{JSON.stringify({ open: drawer.open, tab: drawer.tab, itemId: drawer.itemId, borrowerCode: drawer.borrowerCode, scope: drawer.copilotScope })}</output>
      {drawer.open && drawer.tab === 'item' && drawer.borrowerCode ? <BorrowerTearSheet code={drawer.borrowerCode} /> : null}
    </aside>
  );
}

function show(path: '/portfolio' | '/borrowers' | '/calendar', open: (ref: SourceRef) => void = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const root = createRootRoute({
    component: () => (
      <>
        <main>
          <Outlet />
        </main>
        <DrawerStandIn />
      </>
    ),
  });
  const routeTree = root.addChildren([
    createRoute({ getParentRoute: () => root, path: '/portfolio', component: Portfolio }),
    createRoute({ getParentRoute: () => root, path: '/borrowers', component: Borrowers }),
    createRoute({ getParentRoute: () => root, path: '/calendar', component: Calendar }),
  ]);
  const router = createRouter({ routeTree, history: createMemoryHistory({ initialEntries: [path] }) });
  return render(
    <QueryClientProvider client={client}>
      <SourceContext.Provider value={{ open, close: () => {}, current: null }}>
        <WorkspaceDrawerProvider>
          {/* The app registers its own router type; this small tree stands in for it. */}
          <RouterProvider router={router as never} />
        </WorkspaceDrawerProvider>
      </SourceContext.Provider>
    </QueryClientProvider>,
  );
}

const drawerState = () => JSON.parse(screen.getByTestId('drawer').textContent ?? '{}') as { open: boolean; tab: string; itemId: string | null; borrowerCode: string | null; scope: unknown };
const rowOf = async (name: RegExp) => (await screen.findByRole('link', { name })).closest('tr')!;

beforeEach(() => {
  mockApi();
  window.scrollBy = vi.fn();
  window.scrollTo = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

/* ── Portfolio ────────────────────────────────────────────────────────── */

describe('portfolio table', () => {
  it('opens the borrower tear-sheet from a row, by click or Enter, and keeps the name a link to the borrower page', async () => {
    show('/portfolio');
    const row = await rowOf(/^Kestrel Bay Packaging Corp\.$/);
    expect(within(row).getByRole('link', { name: 'Kestrel Bay Packaging Corp.' })).toHaveAttribute('href', '/borrowers/kestrel-bay-packaging');
    expect(drawerState().open).toBe(false);

    await userEvent.click(row);
    expect(drawerState()).toMatchObject({ open: true, tab: 'item', borrowerCode: 'kestrel-bay-packaging' });
    const sheet = document.querySelector('[data-tear-sheet="kestrel-bay-packaging"]') as HTMLElement;
    expect(within(sheet).getByRole('heading', { level: 2, name: 'Kestrel Bay Packaging Corp.' })).toBeInTheDocument();
    expect(row).toHaveAttribute('aria-selected', 'true');

    const other = await rowOf(/^Sablewood Dental Management, LLC$/);
    other.focus();
    await userEvent.keyboard('{Enter}');
    expect(drawerState().borrowerCode).toBe('sablewood-dental');
    expect(other).toHaveAttribute('aria-selected', 'true');
    expect(row).toHaveAttribute('aria-selected', 'false');
  });

  it('tags a breach in red and a variance in amber, and leaves a compliant row with a dot and a word', async () => {
    show('/portfolio');
    const breach = await rowOf(/^Kestrel Bay/);
    expect(breach.querySelector('[data-tag]')).toHaveAttribute('data-tag', 'breach');
    expect(breach.querySelector('[data-tag]')).toHaveTextContent('Breach, reported compliant');

    const variance = await rowOf(/^Quillfeather/);
    expect(variance.querySelectorAll('[data-tag]')).toHaveLength(1);
    expect(variance.querySelector('[data-tag]')).toHaveAttribute('data-tag', 'attention');

    const compliant = await rowOf(/^Sablewood/);
    expect(compliant.querySelector('[data-tag]')).toBeNull();
    expect(within(compliant).getByText('Compliant')).toBeInTheDocument();

    const untested = await rowOf(/^Ashgrove/);
    expect(untested.querySelector('[data-tag]')).toBeNull();
    expect(within(untested).getByText('Not tested yet')).toBeInTheDocument();
  });

  it('shows the headroom the API stored, opens that fact’s source, and draws the meter from the same fact', async () => {
    const open = vi.fn();
    show('/portfolio', open);
    const row = await rowOf(/^Kestrel Bay/);
    const figure = within(row).getByRole('button', { name: /^−4\.0%, Total Leverage Ratio, headroom, At 30 Sep 2026\. Calculated by code\. Show source\.$/ });
    expect(figure).toHaveAttribute('data-fact', 'h-kestrel-leverage');
    await userEvent.click(figure);
    expect(open).toHaveBeenCalledWith({ type: 'fact', id: 'h-kestrel-leverage' });
    // the figure acts for itself: its click does not also open the row
    expect(drawerState().open).toBe(false);

    // red below zero, green with room to spare; the words on the meter are the stored figure
    expect(within(row).getByRole('img', { name: 'Total Leverage Ratio, headroom −4.0%' }).firstElementChild?.getAttribute('style')).toContain('var(--red-mark)');
    const roomy = await rowOf(/^Sablewood/);
    expect(within(roomy).getByRole('button', { name: /^49\.2%, Total Leverage Ratio, headroom/ })).toHaveAttribute('data-fact', 'h-sable-leverage');
    expect(within(roomy).getByRole('img', { name: 'Total Leverage Ratio, headroom 49.2%' }).firstElementChild?.getAttribute('style')).toContain('var(--green-mark)');

    // nothing tested: a dash and the reason, never a zero and never a meter
    const untested = await rowOf(/^Ashgrove/);
    expect(within(untested).getByText('No covenant tested for the latest period')).toBeInTheDocument();
    expect(within(untested).queryByRole('img')).toBeNull();
    expect(within(untested).queryByText(/0\.0%/)).toBeNull();
  });

  it('filters the table from a covenant count, and clears it again', async () => {
    show('/portfolio');
    await rowOf(/^Sablewood/);
    const count = screen.getByRole('button', { name: 'Breach, reported compliant: 3 tests. Show the borrowers whose worst result this is.' });
    await userEvent.click(count);
    expect(count).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByRole('link', { name: /^Sablewood/ })).toBeNull();
    expect(screen.getByRole('link', { name: /^Kestrel Bay/ })).toBeInTheDocument();
    expect(screen.getByText(/1 of 4 borrowers/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Clear filter' }));
    expect(count).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('link', { name: /^Sablewood/ })).toBeInTheDocument();
  });

  it('shows every count on the summary cards as the API gave it', async () => {
    show('/portfolio');
    const cards = await screen.findByRole('region', { name: 'Portfolio figures' });
    expect(within(cards).getByRole('img', { name: 'Covenant tests by outcome: Breach, reported compliant 3, Breach 1, Compliant, variance 3, Compliant 39' })).toBeInTheDocument();
    expect(within(cards).getByRole('img', { name: 'Open items by severity: Critical 4, High 8, Medium 1' })).toBeInTheDocument();
    expect(within(cards).getByRole('link', { name: 'Critical: 4 open items. Open them in the command centre.' })).toHaveAttribute('href', '/command-centre?severity=critical');
    expect(within(cards).getByRole('button', { name: /^573\.5, Total commitment across the book/ })).toBeInTheDocument();
    expect(within(cards).getByRole('button', { name: /^128\.4, Lines of credit outstanding across the book/ })).toBeInTheDocument();
  });
});

describe('borrower directory', () => {
  it('carries the same tag, headroom fact and tear-sheet as the portfolio', async () => {
    show('/borrowers');
    const row = await rowOf(/^Kestrel Bay/);
    expect(row.querySelector('[data-tag]')).toHaveAttribute('data-tag', 'breach');
    expect(within(row).getByRole('button', { name: /^−4\.0%, Total Leverage Ratio, headroom/ })).toHaveAttribute('data-fact', 'h-kestrel-leverage');
    expect((await rowOf(/^Sablewood/)).querySelector('[data-tag]')).toBeNull();
    await userEvent.click(row);
    expect(drawerState()).toMatchObject({ open: true, borrowerCode: 'kestrel-bay-packaging' });
  });
});

/* ── Tear-sheet ───────────────────────────────────────────────────────── */

describe('borrower tear-sheet', () => {
  async function openSheet() {
    show('/portfolio');
    await userEvent.click(await rowOf(/^Kestrel Bay/));
    const sheet = document.querySelector('[data-tear-sheet="kestrel-bay-packaging"]') as HTMLElement;
    await waitFor(() => expect(sheet).toHaveAttribute('data-ready'));
    return within(sheet);
  }

  it('shows who the borrower is, its exposure as stored facts, and the latest period’s covenants with their meters', async () => {
    const sheet = await openSheet();
    expect(sheet.getByText(/Manufacturing · Risk rating/)).toHaveTextContent('Manufacturing · Risk rating 6');
    expect(sheet.getByRole('button', { name: /^10,989, Line of credit, outstanding/ })).toHaveAttribute('data-fact', 'f-kestrel-line');
    expect(sheet.getByRole('button', { name: /^15,500, Line of credit, commitment/ })).toHaveAttribute('data-fact', 'f-kestrel-commitment');
    expect(sheet.getByRole('button', { name: /^22,125, Term loan, outstanding/ })).toHaveAttribute('data-fact', 'f-kestrel-term');
    expect(sheet.getByRole('button', { name: /^4,511, Availability/ })).toHaveAttribute('data-fact', 'f-kestrel-availability');

    const leverage = sheet.getByText('Total Leverage Ratio').closest('li')!;
    expect(leverage.querySelector('[data-tag]')).toHaveAttribute('data-tag', 'breach');
    expect(within(leverage).getByRole('button', { name: /^2\.60x, Total Leverage Ratio,/ })).toHaveAttribute('data-fact', 'v-leverage');
    expect(within(leverage).getByRole('button', { name: /^2\.50x, Total Leverage Ratio, threshold in force/ })).toHaveAttribute('data-fact', 'th-leverage');
    expect(within(leverage).getByRole('button', { name: /^−4\.0%, Total Leverage Ratio, headroom/ })).toHaveAttribute('data-fact', 'h-kestrel-leverage');
    expect(within(leverage).getByRole('img', { name: 'Total Leverage Ratio, headroom −4.0%' })).toBeInTheDocument();

    // compliant with thin headroom: no tag, an amber meter
    const current = sheet.getByText('Current Ratio').closest('li')!;
    expect(current.querySelector('[data-tag]')).toBeNull();
    expect(within(current).getByRole('img', { name: 'Current Ratio, headroom 7.2%' }).firstElementChild?.getAttribute('style')).toContain('var(--amber-mark)');
    // the earlier period's test is not on the sheet
    expect(sheet.queryByRole('button', { name: /^2\.04x/ })).toBeNull();

    expect(sheet.getByText('Covenant testing')).toBeInTheDocument();
    expect(sheet.getByText('Needs a person').closest('[data-tag]')).toHaveAttribute('data-tag', 'attention');
    expect(sheet.getByText(/open early warning signals/)).toHaveTextContent('7 open early warning signals');
    expect(sheet.getByRole('link', { name: 'Open the borrower page' })).toHaveAttribute('href', '/borrowers/kestrel-bay-packaging');
  });

  it('opens an open item as the exception, and asks the Copilot about this borrower', async () => {
    const sheet = await openSheet();
    await userEvent.click(sheet.getByRole('button', { name: 'Ask Copilot about Kestrel Bay Packaging Corp.' }));
    expect(drawerState()).toMatchObject({ open: true, tab: 'copilot', scope: { kind: 'borrower', code: 'kestrel-bay-packaging' } });

    // back on the sheet, an open item opens as the exception in the drawer
    await userEvent.click(await rowOf(/^Kestrel Bay/));
    const again = within(document.querySelector('[data-tear-sheet="kestrel-bay-packaging"]') as HTMLElement);
    await userEvent.click(await again.findByRole('button', { name: 'Critical: Total Leverage Ratio fails but the certificate reports compliance. Open the exception.' }));
    expect(drawerState()).toMatchObject({ open: true, tab: 'item', itemId: 'w-mismatch', borrowerCode: null });
  });
});

/* ── Calendar ─────────────────────────────────────────────────────────── */

describe('calendar', () => {
  it('tags an overdue requirement in amber with the API’s days late, and leaves the rest plain', async () => {
    show('/calendar');
    const overdue = await rowOf(/^Kestrel Bay/);
    expect(overdue.querySelectorAll('[data-tag]')).toHaveLength(1);
    expect(overdue.querySelector('[data-tag]')).toHaveAttribute('data-tag', 'attention');
    expect(overdue.querySelector('[data-tag]')).toHaveTextContent('Overdue');
    expect(within(overdue).getByText('18 days late')).toBeInTheDocument();

    const due = await rowOf(/^Quillfeather/);
    expect(due.querySelector('[data-tag]')).toBeNull();
    expect(within(due).getByText('Due')).toBeInTheDocument();

    // every status, including one the book never tracked, without a tag and without breaking the page
    await userEvent.click(screen.getByRole('button', { name: /^All/ }));
    const received = await rowOf(/^Sablewood/);
    expect(received.querySelector('[data-tag]')).toBeNull();
    expect(within(received).getByText('Received')).toBeInTheDocument();
    expect(within(received).getByText(/on time/)).toBeInTheDocument();
    expect(within(await rowOf(/^Ashgrove/)).getByText('Not tracked')).toBeInTheDocument();
    expect(document.querySelectorAll('[data-tag="breach"]')).toHaveLength(0);
  });

  it('offers the status filter as buttons that can wrap, with the API’s rows counted', async () => {
    show('/calendar');
    const filter = await screen.findByRole('group', { name: 'Status' });
    expect(filter).toHaveClass('flex-wrap');
    expect(within(filter).getAllByRole('button').map((button) => button.textContent)).toEqual(['Outstanding2', 'Overdue1', 'Due1', 'Received1', 'All4']);
    expect(within(filter).getByRole('button', { name: /^Outstanding/ })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(within(filter).getByRole('button', { name: /^Overdue/ }));
    expect(screen.getByText('1 of 4 requirements')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^Quillfeather/ })).toBeNull();
  });

  it('opens the borrower tear-sheet from a row', async () => {
    show('/calendar');
    await userEvent.click(await rowOf(/^Kestrel Bay/));
    expect(drawerState()).toMatchObject({ open: true, tab: 'item', borrowerCode: 'kestrel-bay-packaging' });
  });
});
