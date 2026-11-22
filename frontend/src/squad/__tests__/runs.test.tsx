import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { BorrowerRow } from '@/api/schema';
import { Runs } from '../clientfile/Runs';

const h = vi.hoisted(() => ({ runs: [] as unknown[], detailError: false }));
vi.mock('../api/hooks', () => ({
  useClientRuns: () => ({ data: h.runs, isPending: false, error: null }),
  useRunDetail: (id: string | null) => (h.detailError ? { data: undefined, error: new Error('gone'), isPending: false }
    : { data: id ? { id, agent_label: id === 'r9' ? 'Review agent' : 'Certificate reader agent', task_label: 'Prepare review', status_label: 'Completed', created_at: '2026-01-01T08:00:00Z', error_words: null, guardrail_notes: [], steps: [{ id: 's1', n: 1, words: 'Tool: read page' }] } : undefined, error: null, isPending: !id }),
}));
vi.mock('../thread/Time', () => ({ Time: () => <span>when</span> }));

const RUN = { id: 'r1', agent_label: 'Certificate reader agent', task_label: 'Read certificate', status_label: 'Completed', created_at: '2026-11-21T08:00:00Z', error_words: null, guardrail_notes: [{ words: 'quote on page · pass' }] };
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
    expect(await screen.findByText(/Tool: read page/)).toBeInTheDocument();
  });

  it('opens the run a link names (?run=) and says plainly when there is none', async () => {
    h.runs = [RUN];
    mount('/?run=r1');
    expect(await screen.findByText(/Tool: read page/)).toBeInTheDocument();
  });

  it('says a failed run stopped on an error without printing the error', async () => {
    h.runs = [{ ...RUN, error_words: 'The run stopped on an error; administrators can see the detail in Oversight.' }];
    mount('/?run=r1');
    expect(await screen.findByRole('alert')).toHaveTextContent('The run stopped on an error; administrators can see the detail in Oversight.');
  });

  it('says so when no agent has run for this client', async () => {
    h.runs = [];
    mount();
    expect(await screen.findByText('No agent has run for this client yet.')).toBeInTheDocument();
  });

  it('opens a named run that is older than the newest page above the table (final review M9)', async () => {
    h.runs = [RUN];
    mount('/?run=r9');
    const older = await screen.findByRole('region', { name: 'The run the link names' });
    expect(older).toHaveTextContent('Review agent');
    expect(older).toHaveTextContent('Tool: read page');
  });

  it('says so when a run’s steps cannot be loaded, instead of reading for ever', async () => {
    h.runs = [RUN];
    h.detailError = true;
    mount();
    await userEvent.click(await screen.findByRole('button', { name: /Steps of Certificate reader agent/ }));
    expect(await screen.findByText('The steps could not be loaded. Try again in a moment.')).toBeInTheDocument();
    h.detailError = false;
  });
});
