import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Covenants } from '../clientfile/views';

const fact = (id: string, key: string, value: string) => ({ id, key, label: key, value, unit: 'months', kind: 'calculated', status: 'verified', period_end: '2026-10-31', months: 0, borrower_id: 'b1', document_id: null, page: null, calc_run_id: 'c1' });
vi.mock('@/api/hooks', () => ({
  useBorrowerCovenants: () => ({
    isPending: false, error: null,
    data: {
      facts: { v1: fact('v1', 'cov.min_runway_months.value', '13'), t1: fact('t1', 'cov.min_runway_months.threshold', '6'), r1: fact('r1', 'cov.min_runway_months.reported', '12') },
      tests: [
        { id: 't', covenant_name: 'Minimum runway', period_end: '2026-10-31', value_fact_id: 'v1', threshold_fact_id: 't1', headroom_fact_id: null, reported_fact_id: 'r1', outcome: 'compliant', terms_version: null, note: null },
        { id: 'old', covenant_name: 'Minimum runway', period_end: '2026-09-30', value_fact_id: null, threshold_fact_id: null, headroom_fact_id: null, reported_fact_id: null, outcome: 'breach', terms_version: null, note: null },
        { id: 't2', covenant_name: 'Burn multiple', period_end: '2026-10-31', value_fact_id: null, threshold_fact_id: null, headroom_fact_id: null, outcome: 'not_meaningful', terms_version: null, note: 'not_meaningful_cash_flow_positive' },
      ],
    },
  }),
}));
vi.mock('../api/hooks', async () => ({
  useDocumentTypeWords: () => ({ data: { types: {}, unclassified: '', notes: { not_meaningful_cash_flow_positive: 'Not meaningful: cash-flow positive (served)' } } }),
}));

describe('Covenants for a venture client', () => {
  it('renders runway facts in months without throwing and words the stored note from the server table', async () => {
    const root = createRootRoute();
    const route = createRoute({ getParentRoute: () => root, path: '/', component: () => <Covenants borrower={{ id: 'b1', code: 'QFL', name: 'Q' } as never} /> });
    const router = createRouter({ routeTree: root.addChildren([route]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
    expect(await screen.findByText('13.0 months')).toBeInTheDocument();
    expect(screen.getByText('6.0 months')).toBeInTheDocument();
    expect(screen.getByText('Not meaningful: cash-flow positive (served)')).toBeInTheDocument();
  });

  it('shows what the certificate reported beside the calculation, and the earlier periods by outcome', async () => {
    const root = createRootRoute();
    const route = createRoute({ getParentRoute: () => root, path: '/', component: () => <Covenants borrower={{ id: 'b1', code: 'QFL', name: 'Q' } as never} /> });
    const router = createRouter({ routeTree: root.addChildren([route]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
    await screen.findByText('13.0 months');
    expect(screen.getByRole('columnheader', { name: 'Reported' })).toBeInTheDocument();
    expect(screen.getByText('12.0 months')).toBeInTheDocument();
    const history = screen.getByRole('table', { name: 'Earlier periods' });
    expect(history).toHaveTextContent('30 Sep 2026');
    expect(history).toHaveTextContent('Breach');
  });
});
