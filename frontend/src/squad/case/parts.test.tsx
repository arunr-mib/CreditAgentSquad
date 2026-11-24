import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { WorkItemDetail } from '@/api/schema';
import { SeverityTag } from '@/screens/parts';
import { Evidence, Recommendation, RelatedItems } from './parts';

window.scrollTo = () => {};

const item = (over: Partial<WorkItemDetail> = {}): WorkItemDetail =>
  ({
    id: 'w-1',
    borrower_id: 'b-1',
    borrower_name: 'Kestrel Bay Packaging Corp.',
    item_type: 'covenant.reported_mismatch',
    severity: 'critical',
    title: 'Total Leverage Ratio fails but the certificate reports compliance',
    question: 'How should the bank respond?',
    allowed_decisions: ['waiver_requested', 'escalate_to_committee'],
    required_permission: 'decide_breach',
    requires_second_person: false,
    assigned_to: null,
    due_date: null,
    status: 'open',
    evidence: {},
    guardrail_notes: [],
    recommendation: null,
    ...over,
  }) as unknown as WorkItemDetail;

afterEach(() => vi.unstubAllGlobals());

describe('open questions that may change the result', () => {
  const RELATED = [
    {
      id: 'w-amend-1234',
      item_type: 'terms.amendment_unapproved',
      title: 'Second amendment is on file but not approved into terms',
      severity: 'high' as const,
      status: 'open' as const,
      relation: 'An unapproved amendment may change the threshold',
    },
    { id: 'w-held-5678', item_type: 'spread.value_unverified', title: 'Two figures are held', severity: 'medium' as const, status: 'open' as const, relation: 'Held figures feed this ratio' },
  ];

  function related(items: typeof RELATED) {
    const onOpen = vi.fn();
    render(<RelatedItems items={items} headingLevel="h3" onOpen={onOpen} />);
    return onOpen;
  }

  it('lists each related open item, each opening its case', async () => {
    const onOpen = related(RELATED);
    const notice = screen.getByRole('region', { name: 'Open questions that may change this result' });
    expect(notice).toHaveTextContent('An unapproved amendment may change the threshold');
    await userEvent.click(screen.getByRole('button', { name: 'Second amendment is on file but not approved into terms' }));
    expect(onOpen).toHaveBeenCalledWith('w-amend-1234');
  });

  it('shows nothing when there are none', () => {
    related([]);
    expect(screen.queryByRole('region', { name: 'Open questions that may change this result' })).toBeNull();
  });

  it('names each review section the checks withheld and the check that withheld it', async () => {
    // Evidence reads documents and facts through hooks: give it a QueryClient and a fetch that answers empty lists
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, text: async () => '[]' }) as Response));
    const root = createRootRoute();
    const page = createRoute({
      getParentRoute: () => root,
      path: '/',
      component: () => (
        <Evidence
          item={item({
            item_type: 'review.commentary_approval',
            evidence: {
              withheld_sections: [
                { section: 'covenants', withheld_by: 'number check', reason: 'a figure was typed, not referenced' },
                { section: 'outlook', withheld_by: 'policy check', reason: 'the wording was refused' },
              ],
            },
          })}
          code="KBP"
          headingLevel="h3"
        />
      ),
    });
    const router = createRouter({ routeTree: root.addChildren([page]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <RouterProvider router={router as never} />
      </QueryClientProvider>,
    );
    const block = await waitFor(() => {
      const found = document.querySelector('[data-withheld-sections]');
      expect(found).not.toBeNull();
      return found as HTMLElement;
    });
    expect(block).toHaveTextContent('2 sections were withheld');
    expect(block).toHaveTextContent('Covenants · withheld by the number check');
    expect(block).toHaveTextContent('Outlook · withheld by the policy check');
  });
});

describe('a slipped funding round (final review I3)', () => {
  it('shows the amount as the funding event’s recorded value, with its source, never in the title', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, text: async () => '[]' }) as Response));
    const root = createRootRoute();
    const page = createRoute({
      getParentRoute: () => root,
      path: '/',
      component: () => (
        <Evidence item={item({ item_type: 'funding_slipped', title: 'Expected equity round has slipped', evidence: { funding_event_id: 'f-1', kind: 'equity_round', amount: '15000000.00', expected_close: '2026-11-01' } })} code="DFK" headingLevel="h3" />
      ),
    });
    const router = createRouter({ routeTree: root.addChildren([page]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <RouterProvider router={router as never} />
      </QueryClientProvider>,
    );
    const row = await screen.findByText('Equity round');
    expect(row.closest('[data-evidence-row]') ?? row.parentElement).toBeTruthy();
    expect(document.querySelector('[data-evidence="funding"]')).toHaveTextContent('15,000,000');
    expect(document.querySelector('[data-evidence="funding"]')).toHaveTextContent('expected to close 1 Nov 2026');
  });
});

describe('severity', () => {
  it('is a tag where it calls for action and plain text where it does not', () => {
    const { container, rerender } = render(<SeverityTag severity="critical" />);
    expect(container.querySelector('[data-tag="breach"]')).toHaveTextContent('Critical');
    rerender(<SeverityTag severity="high" />);
    expect(container.querySelector('[data-tag="attention"]')).toHaveTextContent('High');
    rerender(<SeverityTag severity="low" />);
    expect(container.querySelector('[data-tag]')).toBeNull();
    expect(container).toHaveTextContent('Low');
  });
});

describe('the run link', () => {
  it('opens the client’s read-only run view with the run named, never Oversight', async () => {
    const root = createRootRoute();
    const page = createRoute({
      getParentRoute: () => root,
      path: '/',
      component: () => <Recommendation recommendation={{ summary: 'Reserve rights.', run_id: 'run-123' } as never} item={item({ agent_run_id: 'run-123' } as never)} headingLevel="h3" code="KBP" />,
    });
    const view = createRoute({ getParentRoute: () => root, path: '/clients/$code/file/$view', component: () => null });
    const router = createRouter({ routeTree: root.addChildren([page, view]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(<RouterProvider router={router as never} />);
    const link = await screen.findByRole('link', { name: 'See the run, step by step' });
    expect(link.getAttribute('href')).toBe('/clients/KBP/file/runs?run=run-123');
  });
});
