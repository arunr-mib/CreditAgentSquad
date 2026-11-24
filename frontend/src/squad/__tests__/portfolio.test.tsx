import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { PortfolioRow } from '../api/types';
import { Portfolio } from '../portfolio/Portfolio';

const row = (code: string, name: string, mine: boolean, value: string | null, note: string | null = null): PortfolioRow => ({
  borrower_id: code, code, name, analyst: mine ? 'Priya Raman' : 'Tomas Keller', mine, open: mine ? 2 : 0,
  measure: { kind: 'rml', label: 'Runway (months)', points: [{ period_end: '2026-10-31', note, fact: value ? { id: `f-${code}`, key: 'metric.rml', label: 'Runway', value, unit: 'count', kind: 'calculated', status: 'verified', period_end: '2026-10-31', months: 0, borrower_id: code, document_id: null, page: null, calc_run_id: 'c' } : null }] },
});
const shown = vi.hoisted(() => ({ owns: true }));
const data = { as_of: '2026-11-21', get owns_clients() { return shown.owns; }, sections: [{ template_id: 'vc-1', title: 'Innovation clients', measure_label: 'Runway (months)', rows: [row('SHT', 'Shortfield Bio, Inc.', true, '7.1'), row('LNG', 'Longwater Robotics, Inc.', false, '22.5'), row('NON', 'Nonesuch Analytics, Inc.', false, null, 'Not meaningful: cash-flow positive')] }] };
vi.mock('../api/hooks', () => ({ usePortfolio: () => ({ data, isPending: false, error: null, refetch: vi.fn() }) }));
vi.mock('@/source/figures', () => ({ FactFigure: ({ fact }: { fact: { value: string } }) => <span>{fact.value} months</span>, Absent: () => <span>Not measured</span> }));

function mount() {
  const root = createRootRoute();
  const page = createRoute({ getParentRoute: () => root, path: '/portfolio', component: Portfolio });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([page, thread]), history: createMemoryHistory({ initialEntries: ['/portfolio'] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

describe('Portfolio', () => {
  it('lists clients in the server\u2019s order, each row opening the client\u2019s thread', async () => {
    mount();
    const table = await screen.findByRole('table', { name: 'Innovation clients' });
    const links = within(table).getAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['Shortfield Bio, Inc.', 'Longwater Robotics, Inc.', 'Nonesuch Analytics, Inc.']);
    expect(links[0]).toHaveAttribute('href', '/clients/SHT');
  });

  it('shows the stored note for an unmeasured client, never a zero', async () => {
    mount();
    expect(await screen.findByText('Not meaningful: cash-flow positive')).toBeInTheDocument();
    expect(screen.queryByText(/^0 months/)).not.toBeInTheDocument();
  });

  it('offers "Only my clients" only to someone the server says owns clients', async () => {
    shown.owns = false;
    mount();
    await screen.findByRole('table', { name: 'Innovation clients' });
    expect(screen.queryByRole('checkbox', { name: 'Only my clients' })).not.toBeInTheDocument();
    shown.owns = true;
  });

  it('words "Only my clients" in a neutral colour: green is for a verified pass (final review M4)', async () => {
    mount();
    const label = (await screen.findByRole('checkbox', { name: 'Only my clients' })).closest('label');
    expect(label).not.toHaveClass('sq-check');
    expect(label).toHaveClass('sq-check-label');
  });

  it('narrows to the analyst\u2019s own clients and back', async () => {
    mount();
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Only my clients' }));
    expect(screen.getAllByRole('link').map((l) => l.textContent)).toEqual(['Shortfield Bio, Inc.']);
    await userEvent.click(screen.getByRole('checkbox', { name: 'Only my clients' }));
    expect(screen.getAllByRole('link')).toHaveLength(3);
  });
});
