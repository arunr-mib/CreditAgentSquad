import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { act, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type * as ApiHooks from '../api/hooks';
import type * as Views from '../clientfile/views';
import type { MeasurePoint } from '../api/types';
import { ClientFile } from '../clientfile/ClientFile';
import { MeasureNow, TrendBars } from '../clientfile/Measure';

const state = vi.hoisted(() => ({ open: vi.fn(), lookupError: false, docs: [{ id: 'd1', title: 'MRR report, October 2026', doc_type: 'mrr_report', page_count: 1, period_end: '2026-10-31', received_date: '2026-11-12', status: 'indexed' }, { id: 'd2', title: 'Odd one', doc_type: 'new_kind', page_count: 1, period_end: null, received_date: null, status: 'indexed' }] as unknown[] }));
vi.mock('@/api/hooks', () => ({
  useBorrowerByCode: (code: string) => state.lookupError ? ({ borrower: undefined, notFound: false, error: new Error('down'), refetch: vi.fn() }) : ({ borrower: code === 'QFL' ? { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', template_id: 'vc-1' } : undefined, notFound: code !== 'QFL', error: null }),
  useDocuments: () => ({ data: state.docs, isPending: false, error: null }),
}));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/source/figures', () => ({ FactFigure: ({ fact }: { fact: { value: string } }) => <span>fact {fact.value}</span>, Absent: ({ reason }: { reason?: string }) => <span>{reason ?? 'Not measured'}</span>, SourcedFigure: () => null }));
vi.mock('../api/hooks', async () => ({
  ...(await vi.importActual<typeof ApiHooks>('../api/hooks')),
  // a wording no local table could produce: the test fails if the client file stops reading the served table
  useDocumentTypeWords: () => ({ data: { types: { mrr_report: 'MRR report (served)' }, unclassified: 'Not yet classified (served)', notes: {} } }),
}));
vi.mock('../clientfile/views', async () => {
  const actual = await vi.importActual<typeof Views>('../clientfile/views');
  return { ...actual, Overview: () => <p>overview</p> };
});

function mount(path: string) {
  const root = createRootRoute();
  const file = createRoute({ getParentRoute: () => root, path: '/clients/$code/file', component: ClientFile });
  const view = createRoute({ getParentRoute: () => root, path: '/clients/$code/file/$view', component: ClientFile, validateSearch: (s: Record<string, unknown>) => ({ document: typeof s.document === 'string' ? s.document : undefined, page: typeof s.page === 'number' ? s.page : undefined }) });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([file, view, thread]), history: createMemoryHistory({ initialEntries: [path] }) });
  return Object.assign(render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>), { router });
}

beforeEach(() => { state.open.mockClear(); state.lookupError = false; });

describe('ClientFile', () => {
  it('names the client, offers every view and the way back to the thread', async () => {
    mount('/clients/QFL/file');
    expect(await screen.findByRole('heading', { level: 1, name: 'Quillfeather Labs, Inc.' })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Client file' });
    expect(within(nav).getByRole('link', { name: 'Covenants' })).toHaveAttribute('href', '/clients/QFL/file/covenants');
    expect(within(nav).getByRole('link', { name: 'Overview' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Back to the thread' })).toHaveAttribute('href', '/clients/QFL');
  });

  it('marks exactly one tab current on a view other than the overview (final review I6)', async () => {
    mount('/clients/QFL/file/documents');
    const nav = await screen.findByRole('navigation', { name: 'Client file' });
    const current = nav.querySelectorAll('[aria-current="page"]');
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent('Documents');
    expect(within(nav).getByRole('link', { name: 'Overview' })).not.toHaveAttribute('aria-current');
  });

  it('says so for an unknown view or client', async () => {
    mount('/clients/QFL/file/nonsense');
    expect(await screen.findByText('There is no such part of the client file.')).toBeInTheDocument();
    mount('/clients/NOPE/file');
    expect(await screen.findByText('There is no client with that code.')).toBeInTheDocument();
  });

  it('lists documents in plain words and opens the one an old link named, beside the file', async () => {
    mount('/clients/QFL/file/documents?document=d1&page=1');
    expect(await screen.findByText('MRR report (served)')).toBeInTheDocument();
    expect(state.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1', page: 1 }));
  });
});

describe('ClientFile, more', () => {
  it('says so when the client list cannot be loaded', async () => {
    state.lookupError = true;
    mount('/clients/QFL/file');
    expect(await screen.findByRole('alert')).toHaveTextContent('The client list could not be loaded.');
  });

  it('shows an unknown document type the way the server words it', async () => {
    mount('/clients/QFL/file/documents');
    expect(await screen.findByText('New kind')).toBeInTheDocument();
  });

  it('says so for a document the link names that is not on file, and carries the quote to the drawer', async () => {
    mount('/clients/QFL/file/documents?document=nope');
    expect(await screen.findByText('That document is not on file for this client.')).toBeInTheDocument();
    expect(state.open).not.toHaveBeenCalled();
  });

  it('opens the page with the quote an old link carried', async () => {
    mount('/clients/QFL/file/documents?document=d1&page=2&quote=Net%20sales');
    await screen.findByText('MRR report (served)');
    expect(state.open).toHaveBeenCalledWith(expect.objectContaining({ documentId: 'd1', page: 2, quote: 'Net sales' }));
  });
});

describe('ClientFile, opening the same document again', () => {
  it('opens it again when the link is followed a second time (each visit carries its own state)', async () => {
    const { router } = mount('/clients/QFL/file/documents?document=d1&page=1');
    await screen.findByText('MRR report (served)');
    expect(state.open).toHaveBeenCalledTimes(1);
    await act(async () => { await router.navigate({ to: '/clients/$code/file/$view', params: { code: 'QFL', view: 'documents' }, search: { document: 'd1', page: 1 } as never, state: { visit: 2 } as never }); });
    await vi.waitFor(() => expect(state.open).toHaveBeenCalledTimes(2));
  });
});

describe('Measure', () => {
  const measured: MeasurePoint = { period_end: '2026-08-31', fact: { id: 'f1', key: 'metric.rml', label: 'Runway', value: '14.2', unit: 'months', kind: 'calculated', status: 'verified', period_end: '2026-08-31', months: 0, borrower_id: 'b1', document_id: null, page: null, calc_run_id: 'c1' }, note: null };
  const unmeasured: MeasurePoint = { period_end: '2026-09-30', fact: null, note: 'Not meaningful: cash-flow positive' };
  const points = [measured, unmeasured];

  it('draws no bar for an unmeasured period and no number of its own', () => {
    const { container } = render(<TrendBars points={points} label="Runway (months)" />);
    const bars = container.querySelectorAll('.sq-bar');
    expect(bars).toHaveLength(2);
    expect(bars[1]).toHaveClass('sq-bar-none');
    expect((bars[1] as HTMLElement).style.height).toBe('');
    expect(container.querySelector('.sq-bars')?.textContent).toBe('');
  });

  it('gives a screen reader each period and its state, not just a count', () => {
    render(<TrendBars points={[points[0]!, points[1]!]} label="Runway (months)" />);
    const list = screen.getByRole('list', { name: 'Runway (months) by period' });
    expect(list).toHaveTextContent('31 Aug 2026: 14.2 months');
    expect(list).toHaveTextContent('30 Sep 2026: Not meaningful: cash-flow positive');
  });

  it('never shows a stored zero or a breached (negative) headroom as missing', () => {
    const at = (value: string, period_end: string): MeasurePoint => ({ period_end, note: null, fact: { ...measured.fact!, id: `f-${period_end}`, value, period_end } });
    const { container } = render(<TrendBars points={[at('0.12', '2026-08-31'), at('0', '2026-09-30'), at('-0.08', '2026-10-31'), unmeasured]} label="Tightest covenant headroom" />);
    expect([...container.querySelectorAll('.sq-bar')].map((b) => b.getAttribute('data-point'))).toEqual(['measured', 'low', 'low', 'none']);
  });

  it('shows the stored note, never a zero, when the latest point has no figure', () => {
    render(<MeasureNow series={{ kind: 'rml', label: 'Runway (months)', points }} />);
    expect(screen.getByText('Not meaningful: cash-flow positive')).toBeInTheDocument();
    expect(screen.queryByText(/^0/)).not.toBeInTheDocument();
  });
});
