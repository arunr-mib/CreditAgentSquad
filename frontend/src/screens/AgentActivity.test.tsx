import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AgentRunRow } from '@/api/schema';
import { AgentActivity, checkMarks, checkResult, formatDuration, HowRunsStart, RunTimeline } from './AgentActivity';

window.scrollTo = () => {}; // jsdom has none; the router calls it on navigation

/** The screen's links and search need a router; this one has only the routes the screen names. */
function inRouter(node: ReactNode, at = '/') {
  const root = createRootRoute();
  const page = (path: string, component: () => ReactNode) => createRoute({ getParentRoute: () => root, path, component });
  const router = createRouter({
    routeTree: root.addChildren([
      page('/', () => node),
      page('/agent-activity', () => node),
      page('/borrowers', () => null),
      page('/borrowers/$code', () => null),
    ]),
    history: createMemoryHistory({ initialEntries: [at] }),
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router as never} />
    </QueryClientProvider>,
  );
}

const run = (over: Partial<AgentRunRow> & Pick<AgentRunRow, 'id' | 'status'>): AgentRunRow => ({
  agent_name: 'covenant',
  agent_version: '1',
  model: 'claude-opus-5-5',
  served_model: 'claude-opus-5-5',
  task: 'investigate_covenant_exception',
  borrower_id: 'b-1',
  borrower_name: 'Briarstone Beverage Company',
  borrower_code: 'briarstone-beverage',
  cycle_id: null,
  period_end: '2026-09-30',
  steps_count: 7,
  input_tokens: 48210,
  output_tokens: 2114,
  cache_read_tokens: 0,
  llm_mode: 'live',
  guardrail_notes: [],
  error: null,
  created_at: '2026-11-17T14:37:02.000+00:00',
  finished_at: '2026-11-17T14:37:43.250+00:00',
  duration_ms: 41250,
  ...over,
});

const note = (check: string, action: string) => ({ layer: 'x', check, action, detail: '' }) as unknown as AgentRunRow['guardrail_notes'][number];

const RUNS: AgentRunRow[] = [
  run({ id: 'checked', status: 'completed', guardrail_notes: [note('footing', 'passed'), note('figure_untraceable', 'dropped'), note('quote_not_on_page', 'claim_dropped'), note('quote_not_on_page', 'claim_dropped')] }),
  run({ id: 'unchecked', status: 'completed', created_at: '2026-11-17T14:21:40.000+00:00' }),
  run({ id: 'failed', status: 'failed', agent_name: 'copilot', task: 'answer_question', borrower_name: null, borrower_code: null, period_end: null, created_at: '2026-11-17T15:02:11.000+00:00', duration_ms: 707 }),
  run({ id: 'refused', status: 'refused', created_at: '2026-11-16T08:48:19.000+00:00' }),
  run({ id: 'abstained', status: 'abstained', created_at: '2026-11-16T09:12:05.000+00:00', guardrail_notes: [note('step_cap', 'abstain')] }),
  run({ id: 'running', status: 'running', created_at: '2026-11-16T09:30:00.000+00:00', finished_at: null, duration_ms: null }),
];

const row = (container: HTMLElement, id: string) => container.querySelector<HTMLElement>(`[data-run="${id}"]`)!;

afterEach(() => vi.unstubAllGlobals());

describe('the run timeline', () => {
  it('shows a mark only for a check the run’s record names, with the result recorded there', async () => {
    const { container } = inRouter(<RunTimeline runs={RUNS} selectedId={null} onSelect={() => {}} />);
    await screen.findAllByText('Investigate a covenant exception');

    const checked = [...row(container, 'checked').querySelectorAll<HTMLElement>('[data-check]')];
    expect(checked.map((mark) => [mark.dataset.check, mark.dataset.result])).toEqual([
      ['footing', 'passed'],
      ['figure_untraceable', 'changed'],
      ['quote_not_on_page', 'changed'],
    ]);
    expect(checked[0]).toHaveTextContent('Footing: passed');
    expect(checked[1]).toHaveTextContent('Figure untraceable: dropped');
    expect(checked[2]).toHaveTextContent('Quote not on page: claim dropped ×2');

    // a run whose record names no check gets no mark at all, and says so
    const unchecked = row(container, 'unchecked');
    expect(unchecked.querySelectorAll('[data-check]')).toHaveLength(0);
    expect(within(unchecked).getByText('No guardrail check is named on this run’s record.')).toBeVisible();

    // the only "passed" on the page is the one the record names
    expect(container.querySelectorAll('[data-result="passed"]')).toHaveLength(1);
    expect(row(container, 'abstained').querySelector('[data-check]')).toHaveAttribute('data-result', 'blocked');
    expect(row(container, 'abstained')).toHaveTextContent('Step cap: abstained');
  });

  it('tags a run that failed or was refused, and leaves every other state as plain text', async () => {
    const { container } = inRouter(<RunTimeline runs={RUNS} selectedId={null} onSelect={() => {}} />);
    await screen.findAllByText('Investigate a covenant exception');

    expect(row(container, 'failed').querySelector('[data-tag]')).toHaveAttribute('data-tag', 'attention');
    expect(row(container, 'failed').querySelector('[data-tag]')).toHaveTextContent('Failed');
    expect(row(container, 'refused').querySelector('[data-tag]')).toHaveTextContent('Refused');
    for (const [id, word] of [
      ['checked', 'Completed'],
      ['unchecked', 'Completed'],
      ['abstained', 'Abstained'],
      ['running', 'Running'],
    ] as const) {
      expect(row(container, id).querySelector('[data-tag]')).toBeNull();
      expect(within(row(container, id)).getByText(word)).toBeVisible();
    }
  });

  it('groups runs by day, newest first, with the task in plain words, the borrower as a link and the readings as recorded', async () => {
    const onSelect = vi.fn();
    const { container } = inRouter(<RunTimeline runs={RUNS} selectedId="checked" onSelect={onSelect} />);
    await screen.findAllByText('Investigate a covenant exception');

    expect(screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)).toEqual(['Tuesday 17 Nov 20263 runs', 'Monday 16 Nov 20263 runs']);
    expect([...container.querySelectorAll<HTMLElement>('[data-run]')].map((item) => item.dataset.run)).toEqual(['failed', 'checked', 'unchecked', 'running', 'abstained', 'refused']);

    const checked = row(container, 'checked');
    expect(within(checked).getByText('Covenant agent')).toBeVisible();
    expect(within(checked).getByRole('link', { name: 'Briarstone Beverage Company' })).toHaveAttribute('href', '/borrowers/briarstone-beverage');
    expect(within(checked).getByText('41.3 s · 48,210 in · 2,114 out · claude-opus-5-5')).toHaveClass('ident');
    expect(within(checked).getByRole('button', { name: 'Investigate a covenant exception' })).toHaveAttribute('aria-pressed', 'true');

    const failed = row(container, 'failed');
    expect(within(failed).getByText('Answer a question put to the Copilot')).toBeVisible();
    expect(within(failed).getByText('No single borrower')).toBeVisible();
    expect(within(failed).queryByRole('link')).toBeNull();
    // a run still in progress has no duration to show
    expect(within(row(container, 'running')).getByText('48,210 in · 2,114 out · claude-opus-5-5')).toBeVisible();

    await userEvent.click(within(failed).getByRole('button'));
    expect(onSelect).toHaveBeenCalledWith('failed');
  });

  it('reads a check’s result from the recorded action and counts repeats', () => {
    expect(checkResult('passed')).toBe('passed');
    expect(checkResult('abstain')).toBe('blocked');
    expect(checkResult('refuse')).toBe('blocked');
    expect(checkResult('retry')).toBe('changed');
    expect(checkResult('something_new')).toBe('changed'); // never read as a pass
    expect(checkMarks(null)).toEqual([]);
    expect(checkMarks([{ check: 'schema', action: 'retry' }, { check: 'schema', action: 'abstain' }, { check: 'schema', action: 'retry' }]).map((mark) => [mark.action, mark.result, mark.times])).toEqual([
      ['retry', 'changed', 2],
      ['abstain', 'blocked', 1],
    ]);
    expect(formatDuration(707)).toBe('707 ms');
    expect(formatDuration(41250)).toBe('41.3 s');
    expect(formatDuration(126000)).toBe('2 min 06 s');
  });
});

describe('when no agent has run', () => {
  it('says how a run starts and that each run is billable', async () => {
    inRouter(<HowRunsStart connected />);
    expect(await screen.findByText('No agent has run yet')).toBeVisible();
    expect(screen.getByText(/choose “Run … now” beside its monitoring cycle/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Choose a borrower' })).toHaveAttribute('href', '/borrowers');
    expect(screen.getByRole('button', { name: /Ask the Copilot/ })).toBeEnabled();
    expect(screen.getByText('Each run is billable.')).toBeVisible();
  });

  it('says so, with the server’s reason, where no model is connected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const body = url.includes('/agents/status')
          ? { model_connected: false, mode: 'recorded', model: 'claude-opus-5-5', reason: 'This deployment replays recorded model responses and has none stored.' }
          : [];
        return { ok: true, status: 200, text: async () => JSON.stringify(body) } as Response;
      }),
    );
    inRouter(<AgentActivity />, '/agent-activity');
    expect(await screen.findByText('Agents cannot run on this deployment')).toBeVisible();
    expect(screen.getByText(/This deployment replays recorded model responses and has none stored\./)).toBeVisible();
    expect(await screen.findByText('No agent has run yet')).toBeVisible();
    expect(screen.getByRole('button', { name: /Ask the Copilot/ })).toBeDisabled();
  });
});
