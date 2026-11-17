import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { FactSource } from '@/api/schema';
import { ChangeFigure } from './ChangeFigure';
import { SourceContext, type SourceRef } from './context';

const source = (over: Partial<FactSource['fact']> = {}, history: FactSource['history'] = []): FactSource => ({
  fact: {
    id: 'f-tax',
    key: 'sup.cash_taxes_paid',
    label: 'Cash paid for income taxes',
    value: '1089000',
    unit: 'usd',
    kind: 'extracted',
    status: 'verified',
    period_end: '2026-09-30',
    months: 9,
    borrower_id: 'b-1',
    document_id: 'd-1',
    page: 5,
    calc_run_id: null,
    quote: '1,089',
    label_text: 'Cash paid for income taxes',
    scale_as_reported: 1000,
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
    ...over,
  },
  borrower: { id: 'b-1', name: 'Halvorsen Plastics & Molding, Inc.', code: 'halvorsen-plastics' },
  page: null,
  calculation: null,
  clause: null,
  history,
});

function mockPosts(routes: Record<string, { status?: number; body: unknown }>) {
  const calls: Array<{ url: string; body: unknown }> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') calls.push({ url, body: JSON.parse(String(init.body)) });
      const hit = Object.entries(routes).find(([path]) => url.startsWith(path));
      const status = hit?.[1].status ?? (hit ? 200 : 404);
      return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(hit?.[1].body ?? { detail: 'Not found' }) } as Response;
    }),
  );
  return calls;
}

function show(data: FactSource, open: (ref: SourceRef) => void = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SourceContext.Provider value={{ open, close: () => {}, current: null }}>
        <ChangeFigure data={data} />
      </SourceContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('correcting or rejecting the figure in the source drawer', () => {
  it('offers neither for a calculated figure, and says where the correction belongs', () => {
    show(source({ kind: 'calculated', calc_run_id: 'c-1', document_id: null, page: null }));
    expect(screen.getByText(/^Calculated by code; correct the figure it was calculated from\./)).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('offers neither for a superseded version, and leads to the figure on file now', async () => {
    const open = vi.fn();
    show(
      source({ status: 'superseded' }, [
        { id: 'f-new', value: '4356000', unit: 'usd', kind: 'manual', status: 'confirmed', created_at: '2026-11-17T09:00:00', reason: 'Notes page', relation: 'later', entered_by: 'Priya Raman' },
        { id: 'f-tax', value: '1089000', unit: 'usd', kind: 'extracted', status: 'superseded', created_at: '2026-11-17T08:00:00', reason: null, relation: 'this', entered_by: null },
      ]),
      open,
    );
    expect(screen.getByText('This version is superseded. Only the figure on file now can be corrected or rejected.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Correct this figure|Reject this figure/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Open the figure on file now' }));
    expect(open).toHaveBeenCalledWith({ type: 'fact', id: 'f-new' });
  });

  it('records a correction with its reason, then shows the new figure and what was recalculated', async () => {
    const open = vi.fn();
    const calls = mockPosts({
      '/api/v1/facts/f-tax/correct': {
        body: {
          id: 'f-new',
          borrower_id: 'b-1',
          key: 'sup.cash_taxes_paid',
          value: '4356000',
          unit: 'usd',
          kind: 'manual',
          status: 'confirmed',
          period_end: '2026-09-30',
          months: 9,
          recalculation: { retired: 19, totals: 'recalculated', metrics: [], covenants: [{ facility_id: 'l-1', period_end: '2026-09-30', covenant_id: 'fccr', before: 'compliant', after: 'breach_reported_compliant' }] },
        },
      },
      '/api/v1/ui/borrowers/b-1/covenants': { body: { tests: [{ covenant_id: 'fccr', covenant_name: 'Fixed Charge Coverage Ratio' }], facts: {} } },
    });
    show(source(), open);
    await userEvent.click(screen.getByRole('button', { name: 'Correct this figure' }));
    const form = screen.getByRole('form', { name: 'Correct Cash paid for income taxes' });
    const value = within(form).getByLabelText('Value, in whole US dollars');
    expect(value).toHaveValue('1089000');
    await userEvent.clear(value);
    await userEvent.type(value, '4,356,000');
    await userEvent.type(within(form).getByLabelText('Reason (required)'), 'Notes page reports nine months.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the correction' }));

    expect(await screen.findByText('Corrected. On file now:')).toBeInTheDocument();
    expect(calls).toEqual([{ url: '/api/v1/facts/f-tax/correct', body: { value: '4356000', reason: 'Notes page reports nine months.' } }]);
    const note = screen.getByRole('status');
    expect(note).toHaveTextContent('19 results calculated from the old figure were retired.');
    expect(await within(note).findByRole('listitem', { name: 'Fixed Charge Coverage Ratio, Q3 2026: Compliant → Breach, reported compliant' })).toBeInTheDocument();
    // The new figure is itself a figure with a source.
    await userEvent.click(screen.getByRole('button', { name: '$4,356,000, Cash paid for income taxes. Entered by a person. Show source.' }));
    expect(open).toHaveBeenCalledWith({ type: 'fact', id: 'f-new' });
  });

  it('will not send a rejection without a reason, and shows the server’s refusal in its own words', async () => {
    const calls = mockPosts({ '/api/v1/facts/f-tax/reject': { status: 422, body: { detail: 'a calculated figure cannot be rejected; reject the figure it was calculated from' } } });
    show(source());
    await userEvent.click(screen.getByRole('button', { name: 'Reject this figure' }));
    const form = screen.getByRole('form', { name: 'Reject Cash paid for income taxes' });
    expect(within(form).queryByLabelText(/^Value/)).toBeNull();
    const reason = within(form).getByLabelText('Reason (required)');
    expect(reason).toHaveFocus();
    await userEvent.click(within(form).getByRole('button', { name: 'Record the rejection' }));
    expect(reason).toHaveAccessibleDescription('A reason is required. It is recorded in the ledger with your name.');
    expect(calls).toEqual([]);

    await userEvent.type(reason, 'Read from the wrong column.');
    await userEvent.click(within(form).getByRole('button', { name: 'Record the rejection' }));
    expect(await within(form).findByRole('alert')).toHaveTextContent(
      'Not recorded: the server refused this. The server said: “a calculated figure cannot be rejected; reject the figure it was calculated from”',
    );
    expect(calls).toEqual([{ url: '/api/v1/facts/f-tax/reject', body: { reason: 'Read from the wrong column.' } }]);
  });
});
