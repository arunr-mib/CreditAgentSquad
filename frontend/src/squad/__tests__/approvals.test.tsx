import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Approvals } from '../approvals/Approvals';

const rows = [{ work_item_id: 'w1', borrower_id: 'b1', borrower_code: 'QFL', borrower_name: 'Quillfeather Labs, Inc.', title: 'Quillfeather Labs, Inc.: cash below minimum', subject: 'Cash below minimum', severity: 'high', due_date: null, view: 'Recommend reserving rights.', routed_by: 'Priya Raman', routed_at: '2026-11-21T09:00:00Z', returns: 0 }];
vi.mock('../api/hooks', () => ({ useApprovals: () => ({ data: rows, isPending: false, error: null, refetch: vi.fn() }) }));
vi.mock('../case/CasePanel', () => ({ CasePanel: ({ workItemId }: { workItemId: string }) => <p>case {workItemId}</p> }));
vi.mock('../thread/Trail', () => ({ Trail: ({ workItemId }: { workItemId: string }) => <p>how Squad got here for {workItemId}</p> }));

function mount(path: string) {
  const root = createRootRoute();
  const route = createRoute({ getParentRoute: () => root, path: '/approvals', component: Approvals, validateSearch: (s: Record<string, unknown>) => ({ case: typeof s.case === 'string' ? s.case : undefined }) });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([route, thread]), history: createMemoryHistory({ initialEntries: [path] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

describe('Approvals', () => {
  it('counts what waits, shows the analyst’s view, and opens the case beside the list', async () => {
    mount('/approvals?case=w1');
    expect(await screen.findByText('1 decision waits for you')).toBeInTheDocument();
    expect(screen.getByText(/Recommend reserving rights/)).toBeInTheDocument();
    expect(screen.getByText('case w1')).toBeInTheDocument();
    expect(screen.getByText('how Squad got here for w1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open in quillfeather labs, inc\.’s thread/i })).toHaveAttribute('href', '/clients/QFL?case=w1');
  });

  it('names the client once, shows the decision’s subject in full and lets the view wrap (final review I5)', async () => {
    mount('/approvals');
    const row = await screen.findByRole('link', { name: /Cash below minimum/ });
    expect(row.textContent?.split('Quillfeather Labs, Inc.').length).toBe(2);
    expect(row.querySelector('.sq-rowtitle')).toHaveTextContent('Quillfeather Labs, Inc. · Cash below minimum');
    expect(row.querySelector('.sq-rowtext')).not.toBeNull();
    expect(row.querySelector('.sq-block')).toHaveTextContent('Priya Raman: Recommend reserving rights.');
  });
});
