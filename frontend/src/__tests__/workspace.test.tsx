import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, errorMessage, onUnauthorized, request, withQuery } from '@/api/client';
import type { Calculation, FactSummary, LedgerEvent } from '@/api/schema';
import { decisionLabel, decisionNeedsReason, formatTimestamp, humanize, itemGroup, periodLabel, quarterLabel, toFact } from '@/domain/labels';
import { describeEvent } from '@/squad/oversight/describeEvent';
import { AgentBody, referencedFactIds } from '@/source/AgentBody';
import { CalculationBreakdown } from '@/source/CalculationBreakdown';
import { SourceContext, type SourceRef } from '@/source/context';
import { FactFigure } from '@/source/figures';

const fact = (over: Partial<FactSummary>): FactSummary => ({
  id: 'f-1',
  key: 'is.revenue',
  label: 'Net revenue',
  value: '100900000',
  unit: 'usd',
  kind: 'seeded',
  status: 'verified',
  period_end: '2026-09-30',
  months: 9,
  borrower_id: 'b-1',
  document_id: null,
  page: null,
  calc_run_id: null,
  ...over,
});

function mockFetch(routes: Record<string, { status?: number; body: unknown }>) {
  const calls: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url);
      const hit = Object.entries(routes).find(([path]) => url.startsWith(path));
      const status = hit?.[1].status ?? (hit ? 200 : 404);
      return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(hit?.[1].body ?? { detail: 'Not found' }) } as Response;
    }),
  );
  return calls;
}

function withProviders(children: ReactNode, open: (ref: SourceRef) => void = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <SourceContext.Provider value={{ open, close: () => {}, current: null }}>{children}</SourceContext.Provider>
    </QueryClientProvider>
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('API client', () => {
  it('builds a query string without empty parameters', () => {
    expect(withQuery('/work-items', { status: 'open', borrower_id: undefined, item_type: '' })).toBe('/work-items?status=open');
    expect(withQuery('/clock')).toBe('/clock');
  });

  it('returns the server’s own words on a refusal and tells listeners when the session has ended', async () => {
    mockFetch({ '/api/v1/work-items/x/decide': { status: 403, body: { detail: 'your role cannot decide this item (decide_breach)' } }, '/api/v1/borrowers': { status: 401, body: { detail: 'Sign in to continue.' } } });
    const refusal = await request('/work-items/x/decide', { method: 'POST', body: {} }).catch((error: unknown) => error);
    expect(refusal).toBeInstanceOf(ApiError);
    expect((refusal as ApiError).status).toBe(403);
    expect(errorMessage(refusal)).toBe('your role cannot decide this item (decide_breach)');

    const ended = vi.fn();
    const stop = onUnauthorized(ended);
    await request('/borrowers').catch(() => undefined);
    expect(ended).toHaveBeenCalledTimes(1);
    await request('/borrowers', { quiet401: true }).catch(() => undefined);
    expect(ended).toHaveBeenCalledTimes(1);
    stop();
  });

  it('says so when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')));
    const error = await request('/clock').catch((caught: unknown) => caught);
    expect(errorMessage(error)).toMatch(/could not be reached/);
  });
});

describe('labels and the fact adapter', () => {
  it('moves the decimal point of a percentage exactly, without a float', () => {
    expect(toFact(fact({ unit: 'pct', value: '0.072', key: 'cov.current_ratio.headroom_pct' })).value).toBe('7.200000');
    expect(toFact(fact({ unit: 'pct', value: '-0.0400' })).value).toBe('-4.000000');
    expect(toFact(fact({})).value).toBe('100900000');
  });

  it('keeps a seeded fact marked as seeded, never as read from a document', () => {
    expect(toFact(fact({})).provenance.kind).toBe('seeded');
    expect(toFact(fact({ kind: 'calculated', calc_run_id: 'c-1' })).provenance).toMatchObject({ kind: 'calculated', calcId: 'c-1' });
  });

  it('names periods, decisions and identifiers in plain words', () => {
    expect(periodLabel('2026-09-30', 9)).toBe('9 months to 30 Sep 2026');
    expect(periodLabel('2025-12-31', 12)).toBe('Year to 31 Dec 2025');
    expect(periodLabel('2026-09-30', 0)).toBe('At 30 Sep 2026');
    expect(quarterLabel('2026-09-30')).toBe('Q3 2026');
    expect(quarterLabel('2026-10-31')).toBe('31 Oct 2026');
    expect(formatTimestamp('2026-11-17T14:37:10.311+00:00')).toBe('17 Nov 2026, 14:37');
    expect(decisionLabel('reservation_of_rights')).toBe('Reserve rights');
    expect(decisionLabel('something_new')).toBe('Something new');
    expect(decisionNeedsReason('not_a_breach')).toBe(true);
    expect(decisionNeedsReason('acknowledged')).toBe(false);
    expect(itemGroup('bb.over_advance')).toBe('borrowing_base');
    expect(humanize('covenant.reported_mismatch')).toBe('Covenant reported mismatch');
  });

  it('describes a ledger event from its payload', () => {
    const event = (action: string, payload: Record<string, unknown>): LedgerEvent => ({ seq: 1, id: 'e', ts: '2026-11-17T14:37:00+00:00', actor_type: 'user', actor_id: 'u', action, entity_type: 'work_item', entity_id: 'w', payload, hash: 'h', note: null });
    expect(describeEvent(event('work_item.decided', { decision: 'reservation_of_rights', reason: 'Certificate overstates EBITDA.' }))).toBe('Reserve rights · “Certificate overstates EBITDA.”');
    expect(describeEvent(event('cycle.stage_changed', { stage: 'covenant_testing', from: 'needs_person', to: 'done' }))).toBe('Covenant testing: needs a person to done');
    expect(describeEvent(event('clock.set', { to: '2026-11-17', from: null }))).toBe('to 17 Nov 2026');
    expect(describeEvent(event('covenant.tested', { covenant: 'total_leverage', outcome: 'breach_reported_compliant', period_end: '2026-09-30' }))).toBe(
      'Total leverage · breach reported compliant · period ended 30 Sep 2026',
    );
  });
});

describe('figures on real data', () => {
  it('opens the source drawer for the fact, and shows a dash, never a zero, when nothing is stored', async () => {
    const open = vi.fn();
    render(
      withProviders(
        <>
          <FactFigure fact={fact({})} scale={1000} unitMark={false} />
          <FactFigure fact={undefined} absent="Not reported" />
        </>,
        open,
      ),
    );
    const figure = screen.getByRole('button', { name: /^100,900, Net revenue, 9 months to 30 Sep 2026\. Loaded from the synthetic book\. Show source\.$/ });
    await userEvent.click(figure);
    expect(open).toHaveBeenCalledWith({ type: 'fact', id: 'f-1' });
    expect(screen.getByText('Not reported')).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('renders agent text with stored facts and flags a reference that does not resolve', async () => {
    const calls = mockFetch({ '/api/v1/ui/facts': { body: { 'f-1': fact({ kind: 'calculated', unit: 'ratio', value: '2.6', label: 'Total Leverage Ratio', months: 0 }) } } });
    expect(referencedFactIds('A {{fact:f-1}} and {{fact:f-2}}.')).toEqual(['f-1', 'f-2']);
    render(withProviders(<AgentBody text="Leverage is {{fact:f-1}} against {{fact:f-2}}." />));
    await waitFor(() => expect(screen.getByRole('button', { name: /^2\.60x, Total Leverage Ratio/ })).toBeInTheDocument());
    expect(screen.getByText(/unresolved f-2/)).toBeInTheDocument();
    expect(calls).toHaveLength(1);
    expect(calls[0]).toContain('ids=f-1%2Cf-2');
  });
});

describe('calculation breakdown', () => {
  const input = (key: string, sign: number, factId: string, periodEnd: string, months: number) => ({ key, name: key, sign, value: '1', fact_id: factId, period_end: periodEnd, months });
  const calc: Calculation = {
    id: 'calc-1',
    formula_key: 'covenant.total_leverage',
    formula_version: 'leverage@terms-v1',
    engine_version: 'calc-1',
    period_end: '2026-09-30',
    error: null,
    created_at: '2026-11-17T08:00:00+00:00',
    created_by_type: 'system',
    created_by_id: 'seed',
    terms_version: { id: 't', version: 1, status: 'approved', effective_from: '2022-05-06' },
    expression: 'Total debt ÷ EBITDA',
    inputs: [],
    steps: [
      { n: 1, op: 'line', name: 'Line of credit', key: 'bs.revolver', basis: 'at the period end', value: '10989000', period_end: '2026-09-30', unit: 'usd', final: false, inputs: [input('bs.revolver', 1, 'debt', '2026-09-30', 0)] },
      { n: 2, op: 'add', name: 'Sum', key: null, basis: null, value: '10989000', period_end: '2026-09-30', unit: 'usd', final: false, inputs: [] },
      { n: 3, op: 'named', name: 'Total debt', key: null, basis: null, value: '10989000', period_end: '2026-09-30', unit: 'usd', final: false, inputs: [] },
      {
        n: 4,
        op: 'line',
        name: 'Net income',
        key: 'is.net_income',
        basis: 'trailing twelve months',
        value: '4866000',
        period_end: '2026-09-30',
        unit: 'usd',
        final: false,
        inputs: [input('is.net_income', 1, 'ni-now', '2026-09-30', 9), input('is.net_income', 1, 'ni-year', '2025-12-31', 12), input('is.net_income', -1, 'ni-prior', '2025-09-30', 9)],
      },
      { n: 5, op: 'named', name: 'EBITDA', key: null, basis: null, value: '4866000', period_end: '2026-09-30', unit: 'usd', final: false, inputs: [] },
      { n: 6, op: 'div', name: 'Ratio', key: null, basis: null, value: '2.2583230579531442', period_end: '2026-09-30', unit: 'ratio', final: true, inputs: [] },
    ],
    addbacks: [],
    outputs: { value: '2.26', passed: true },
    facts: {
      debt: fact({ id: 'debt', key: 'bs.revolver', label: 'Line of credit', value: '10989000', months: 0 }),
      'ni-now': fact({ id: 'ni-now', key: 'is.net_income', label: 'Net income', value: '3241000' }),
      'ni-year': fact({ id: 'ni-year', key: 'is.net_income', label: 'Net income', value: '6328000', period_end: '2025-12-31', months: 12 }),
      'ni-prior': fact({ id: 'ni-prior', key: 'is.net_income', label: 'Net income', value: '4703000', period_end: '2025-09-30' }),
    },
  };

  it('shows each line, the periods a trailing figure is built from, and the rounded result', async () => {
    const open = vi.fn();
    render(withProviders(<CalculationBreakdown calc={calc} resultLabel="Total Leverage Ratio" resultUnit="ratio" />, open));
    const rows = screen.getAllByRole('row').map((row) => row.textContent ?? '');
    // The unnamed sum that "Total debt" names is shown once, under its name.
    expect(rows.filter((text) => text.startsWith('Sum'))).toHaveLength(0);
    expect(rows.some((text) => text.startsWith('Total debt'))).toBe(true);
    const ttm = screen.getByRole('row', { name: /Net income, trailing twelve months/ });
    expect(within(ttm).getByRole('button', { name: /^4,866, Net income/ })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /plus 9 months to 30 Sep 2026/ })).toHaveTextContent('3,241');
    expect(screen.getByRole('row', { name: /plus Year to 31 Dec 2025/ })).toHaveTextContent('6,328');
    expect(screen.getByRole('row', { name: /less 9 months to 30 Sep 2025/ })).toHaveTextContent('4,703');
    // The final row shows the result as the engine rounded it, not the raw quotient.
    const total = screen.getByRole('row', { name: /^Total Leverage Ratio/ });
    expect(total).toHaveTextContent('2.26x');
    expect(total).not.toHaveTextContent('2.2583');

    // A single-period line is the fact itself; a derived line opens the calculation.
    await userEvent.click(screen.getByRole('button', { name: /^10,989, Line of credit, At 30 Sep 2026/ }));
    expect(open).toHaveBeenLastCalledWith({ type: 'fact', id: 'debt' });
    await userEvent.click(within(ttm).getByRole('button'));
    expect(open).toHaveBeenLastCalledWith({ type: 'calculation', id: 'calc-1', title: 'Total Leverage Ratio' });
  });

  it('does not link a calculation’s own lines back to itself inside the source drawer', () => {
    render(withProviders(<CalculationBreakdown calc={calc} resultLabel="Total Leverage Ratio" resultUnit="ratio" selfContained />));
    const ttm = screen.getByRole('row', { name: /Net income, trailing twelve months/ });
    expect(within(ttm).queryByRole('button')).not.toBeInTheDocument();
    expect(within(ttm).getByRole('img', { name: 'Calculation' })).toBeInTheDocument();
  });
});
