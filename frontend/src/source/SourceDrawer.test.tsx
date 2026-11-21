import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { FactSource, FactSummary } from '@/api/schema';
import { useSource } from './context';
import { SourceProvider } from './SourceDrawer';

window.scrollTo = () => {};

const summary = (over: Partial<FactSummary> & Pick<FactSummary, 'id' | 'key' | 'label' | 'value' | 'unit'>): FactSummary => ({
  kind: 'calculated',
  status: 'verified',
  period_end: '2026-09-30',
  months: 12,
  borrower_id: 'b-1',
  document_id: null,
  page: null,
  calc_run_id: 'calc-ratio',
  ...over,
});

const VALUE = summary({ id: 'f-value-1234', key: 'cov.lev.value', label: 'Total Leverage Ratio', value: '1.94', unit: 'ratio' });
const THRESHOLD = summary({ id: 'f-thr-5678', key: 'cov.lev.threshold', label: 'Total Leverage Ratio, threshold in force', value: '1.75', unit: 'ratio' });
const HEADROOM = summary({ id: 'f-head-9abc', key: 'cov.lev.headroom_pct', label: 'Total Leverage Ratio, headroom', value: '-0.1086', unit: 'pct' });

function base(fact: FactSummary, over: Partial<FactSource> = {}, provenance?: 'term' | 'headroom' | null): FactSource {
  return {
    fact: {
      ...fact,
      quote: null,
      label_text: null,
      scale_as_reported: null,
      connector: null,
      record_ref: null,
      as_of: null,
      entered_by: null,
      reason: null,
      note: null,
      confirmed_by: null,
      confirmed_at: null,
      created_at: '2026-11-17T08:00:00',
      agent_run_id: null,
      ...(provenance !== undefined ? { provenance } : {}),
    },
    borrower: { id: 'b-1', name: 'Calder & Finch Staffing Group, LLC', code: 'calder-finch' },
    page: null,
    calculation: null,
    clause: null,
    history: [],
    ...over,
  };
}

const CLAUSE = {
  document_id: null,
  document_title: 'Second amendment',
  doc_type: 'amendment',
  page: 3,
  page_count: 6,
  boxes: [],
  quote: 'Total Leverage Ratio shall not exceed 1.75 to 1.00 from 1 July 2026',
  method: 'cited' as const,
  section: '7.2(a)',
};

const TERM_SOURCE = base(
  THRESHOLD,
  {
    term: {
      covenant_name: 'Total Leverage Ratio',
      operator: '<=',
      unit: 'ratio',
      threshold_in_force: '1.75',
      base_threshold: '2.00',
      steps: [
        { from: '2026-01-01', value: '1.90', in_force: false },
        { from: '2026-07-01', value: '1.75', in_force: true },
      ],
      terms_version: { id: 'tv-1', version: 2, status: 'approved', effective_from: '2026-01-01' },
      clause: CLAUSE as FactSource['clause'],
    },
  },
  'term',
);

const HEADROOM_SOURCE = base(
  HEADROOM,
  {
    headroom: {
      operator: '<=',
      value: '1.94',
      value_fact_id: VALUE.id,
      threshold: '1.75',
      threshold_fact_id: THRESHOLD.id,
      headroom: '-0.19',
      headroom_pct: '-0.1086',
      formula: '(threshold − value) ÷ |threshold|',
      ratio_calculation_id: 'calc-ratio',
    },
  },
  'headroom',
);

function mockApi(routes: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = String(url);
      const hit = Object.entries(routes).find(([prefix]) => path.startsWith(prefix));
      const status = hit ? 200 : 404;
      return { ok: status === 200, status, text: async () => JSON.stringify(hit?.[1] ?? { detail: 'Not found' }) } as Response;
    }),
  );
}

function Opener({ id }: { id: string }) {
  const source = useSource();
  return (
    <button type="button" onClick={() => source.open({ type: 'fact', id })}>
      open
    </button>
  );
}

async function openSource(id: string) {
  const root = createRootRoute();
  const page = createRoute({
    getParentRoute: () => root,
    path: '/',
    component: () => (
      <SourceProvider>
        <Opener id={id} />
      </SourceProvider>
    ),
  });
  const docs = createRoute({ getParentRoute: () => root, path: '/clients/$code/file/$view', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([page, docs]), history: createMemoryHistory({ initialEntries: ['/'] }) });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router as never} />
    </QueryClientProvider>,
  );
  await userEvent.click(await screen.findByRole('button', { name: 'open' }));
  return screen.findByRole('dialog');
}

afterEach(() => vi.unstubAllGlobals());

describe('the source of a covenant threshold', () => {
  it('shows the term in force, its schedule, the terms version and the clause of the step in force', async () => {
    mockApi({ [`/api/v1/ui/facts/${THRESHOLD.id}/source`]: TERM_SOURCE });
    const drawer = await openSource(THRESHOLD.id);
    expect(await within(drawer).findByText('From approved terms', { selector: '.eyebrow' })).toBeInTheDocument();
    const term = within(drawer).getByRole('region', { name: 'Term in force' });
    expect(within(term).getByText('At most 1.75x')).toBeInTheDocument();
    const schedule = within(term).getByRole('list', { name: 'Threshold schedule' });
    const steps = within(schedule).getAllByRole('listitem');
    expect(steps).toHaveLength(3);
    expect(steps[0]).toHaveTextContent('Base');
    expect(steps[0]).toHaveTextContent('2.00x');
    expect(steps[1]).toHaveTextContent('From 1 Jan 2026');
    expect(steps[1]).toHaveTextContent('1.90x');
    expect(steps[2]).toHaveTextContent('From 1 Jul 2026');
    expect(steps[2]).toHaveTextContent('In force');
    expect(steps[1]).not.toHaveTextContent('In force');
    expect(term).toHaveTextContent(/Version 2, approved, effective 1 Jan 2026/);
    expect(term).toHaveTextContent(/Section 7\.2\(a\)/);
    expect(term).toHaveTextContent(/page 3/);
    expect(within(term).getByText(/shall not exceed/)).toBeInTheDocument();
    // The calculation section is not shown for a term.
    expect(within(drawer).queryByRole('region', { name: 'Calculation' })).toBeNull();
    // The record's check says where the figure comes from, in the pass tone.
    expect(within(drawer).getAllByText('From approved terms')).toHaveLength(2);
  });

  it('falls back to the calculation when the API sends no term (older API)', async () => {
    mockApi({ [`/api/v1/ui/facts/${THRESHOLD.id}/source`]: base(THRESHOLD) });
    const drawer = await openSource(THRESHOLD.id);
    expect(await within(drawer).findByText('Calculated by code', { selector: '.eyebrow' })).toBeInTheDocument();
    expect(within(drawer).queryByRole('region', { name: 'Term in force' })).toBeNull();
  });
});

describe('the source of a covenant headroom', () => {
  it('shows the formula, the arithmetic with each input opening its source, and the result', async () => {
    mockApi({
      [`/api/v1/ui/facts/${HEADROOM.id}/source`]: HEADROOM_SOURCE,
      [`/api/v1/ui/facts/${THRESHOLD.id}/source`]: TERM_SOURCE,
      '/api/v1/ui/facts?': { [VALUE.id]: VALUE, [THRESHOLD.id]: THRESHOLD },
    });
    const drawer = await openSource(HEADROOM.id);
    expect(await within(drawer).findByText('Calculated by code', { selector: '.eyebrow' })).toBeInTheDocument();
    const section = within(drawer).getByRole('region', { name: 'Headroom' });
    expect(section).toHaveTextContent(/threshold less the calculated value/i);
    expect(section).toHaveTextContent('(threshold − value) ÷ |threshold|');
    const valueChip = await within(section).findByRole('button', { name: /1\.94x/ });
    const thresholdChip = within(section).getByRole('button', { name: /1\.75x/ });
    expect(valueChip).toBeInTheDocument();
    expect(section).toHaveTextContent('−0.19x');
    expect(section).toHaveTextContent('−10.9%');
    expect(within(section).getByRole('button', { name: /Open the ratio’s calculation/ })).toBeInTheDocument();
    await userEvent.click(thresholdChip);
    expect(await within(screen.getByRole('dialog')).findByRole('region', { name: 'Term in force' })).toBeInTheDocument();
  });

  it('falls back to the current rendering when the API sends no headroom (older API)', async () => {
    mockApi({ [`/api/v1/ui/facts/${HEADROOM.id}/source`]: base(HEADROOM) });
    const drawer = await openSource(HEADROOM.id);
    expect(await within(drawer).findByText('Calculated by code', { selector: '.eyebrow' })).toBeInTheDocument();
    expect(within(drawer).queryByRole('region', { name: 'Headroom' })).toBeNull();
  });
});
