import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { BorrowerRow } from '@/api/schema';
import { Runs } from '../clientfile/Runs';

const h = vi.hoisted(() => ({ runs: [] as unknown[] }));
vi.mock('../api/hooks', () => ({
  useClientRuns: () => ({ data: h.runs, isPending: false, error: null }),
  useRunDetail: (id: string | null) => ({ data: id ? { steps: [{ id: 's1', n: 1, kind: 'tool', name: 'read_page', input_summary: 'page 2', output_summary: 'ok', refused: false }] } : undefined }),
}));
vi.mock('../thread/Time', () => ({ Time: () => <span>when</span> }));

const RUN = { id: 'r1', agent_label: 'Certificate reader agent', task_label: 'Read certificate', status_label: 'Completed', created_at: '2026-11-21T08:00:00Z', error: null, guardrail_notes: [{ words: 'quote on page · pass' }] };
function mount(path = '/') {
  const root = createRootRoute({ component: () => <Runs borrower={{ id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.' } as BorrowerRow} /> });
  const router = createRouter({ routeTree: root.addChildren([createRoute({ getParentRoute: () => root, path: '/', component: () => null })]), history: createMemoryHistory({ initialEntries: [path] }) });
  return render(<RouterProvider router={router as never} />);
}

describe('Runs: what the agents did for this client, read only, for anyone who may see the client', () => {
  it('lists each run in the server’s words and opens its steps', async () => {
    h.runs = [RUN];
    mount();
    expect(await screen.findByText(/Certificate reader agent/)).toBeInTheDocument();
    expect(screen.getByText(/Read certificate/)).toBeInTheDocument();
    expect(screen.getByText('quote on page · pass')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Steps of Certificate reader agent/ }));
    expect(await screen.findByText(/read_page · page 2/)).toBeInTheDocument();
  });

  it('opens the run a link names (?run=) and says plainly when there is none', async () => {
    h.runs = [RUN];
    mount('/?run=r1');
    expect(await screen.findByText(/read_page · page 2/)).toBeInTheDocument();
  });

  it('says so when no agent has run for this client', async () => {
    h.runs = [];
    mount();
    expect(await screen.findByText('No agent has run for this client yet.')).toBeInTheDocument();
  });
});
