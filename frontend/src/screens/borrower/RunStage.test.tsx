import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { BorrowerOverview } from '@/api/schema';
import type { StageId, StageStatus } from '@/api/types';
import { AuthContext } from '@/auth/context';
import { RunStage } from './RunStage';

type Cycle = NonNullable<BorrowerOverview['cycle']>;

function cycle(stage: StageId, statuses: Array<[StageId, StageStatus]>, status = 'open'): Cycle {
  return {
    id: 'c-1',
    stage,
    status,
    period_end: '2026-09-30',
    stages: statuses.map(([id, state]) => ({ stage: id, status: state, open_work_items: 0 })),
  } as unknown as Cycle;
}

function show(value: Cycle, permissions: string[], model: { model_connected: boolean; reason: string }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ mode: 'live', model: 'claude-opus-5-5', ...model }) }) as Response),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = {
    user: null,
    status: 'signed-in' as const,
    can: (permission: string) => permissions.includes(permission),
    signIn: async () => null as never,
    signOut: async () => {},
    retry: () => {},
  };
  return render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <RunStage cycle={value} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

const SPREADING_NEXT = cycle('spreading', [
  ['intake', 'done'],
  ['spreading', 'pending'],
  ['covenant_testing', 'pending'],
]);

describe('running a stage by hand', () => {
  it('is not offered to a role that may not run agents, or on a closed cycle', () => {
    const { container, unmount } = show(SPREADING_NEXT, ['view', 'decide_breach'], { model_connected: true, reason: '' });
    expect(container).toBeEmptyDOMElement();
    unmount();
    expect(show(cycle('closed', [['intake', 'done']], 'closed'), ['run_agents'], { model_connected: true, reason: '' }).container).toBeEmptyDOMElement();
  });

  it('is switched off, with the reason, where no model is connected', async () => {
    show(SPREADING_NEXT, ['run_agents'], { model_connected: false, reason: 'No model key is set for this deployment.' });
    expect(await screen.findByText('Agents cannot run here. No model key is set for this deployment.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Run Spreading now' })).toBeDisabled();
  });

  it('names the stage it will run and says the run is billable and recorded', async () => {
    show(SPREADING_NEXT, ['run_agents'], { model_connected: true, reason: '' });
    expect(await screen.findByText(/Each run is billable and is recorded in the ledger in your name\./)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Run Spreading now' })).toBeEnabled();
  });

  it('does not run past a stage that is waiting for a person', async () => {
    show(
      cycle('spreading', [
        ['intake', 'done'],
        ['spreading', 'needs_person'],
        ['covenant_testing', 'pending'],
      ]),
      ['run_agents'],
      { model_connected: true, reason: '' },
    );
    expect(await screen.findByText(/Spreading is waiting for a person\./)).toBeVisible();
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
