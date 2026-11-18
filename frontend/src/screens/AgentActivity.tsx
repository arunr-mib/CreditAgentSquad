import { useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo } from 'react';
import { useAgentRun, useAgentRuns } from '@/api/hooks';
import type { AgentRunDetail, AgentRunRow } from '@/api/schema';
import { Card, CardHeader, DataTable, EmptyState, formatDate, GuardrailNotes, PageHeader, SkeletonRows, StatusDot, type DataColumn, type StatusTone } from '@/design';
import { formatTimestamp, humanize } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { Def, EmptyCard, ErrorNotice, Load } from './parts';

const STATUS: Record<AgentRunRow['status'], { tone: StatusTone; label: string }> = {
  running: { tone: 'neutral', label: 'Running' },
  completed: { tone: 'neutral', label: 'Completed' },
  abstained: { tone: 'attention', label: 'Abstained' },
  failed: { tone: 'attention', label: 'Failed' },
  refused: { tone: 'attention', label: 'Refused' },
};
const STEP_KIND: Record<string, string> = { model: 'Model call', tool: 'Tool call', guardrail: 'Guardrail', note: 'Note' };

function plainValue(value: unknown): string {
  if (value === null || value === undefined) return 'None';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

function RunDetail({ run }: { run: AgentRunDetail }) {
  const status = STATUS[run.status] ?? { tone: 'neutral' as const, label: humanize(run.status) };
  const refusals = run.steps.filter((step) => step.refused).length;
  return (
    <Card data-agent-run={run.id}>
      <CardHeader
        as="h2"
        eyebrow={
          <span className="text-iris">
            {humanize(run.agent_name)} agent <span className="ident tracking-normal normal-case">{run.agent_version}</span>
          </span>
        }
        title={humanize(run.task)}
        meta={`${run.borrower_name ?? 'Portfolio'}${run.period_end ? ` · period ended ${formatDate(run.period_end)}` : ''} · ${formatTimestamp(run.created_at)} UTC`}
        actions={<StatusDot tone={status.tone} emphasis={status.tone === 'attention'}>{status.label}</StatusDot>}
      />
      <dl className="border-t border-hairline px-4 pb-1">
        <Def label="Model">
          <span className="ident">{run.served_model ?? run.model}</span> · {run.llm_mode} responses
        </Def>
        <Def label="Steps">
          <span className="tnum">{run.steps_count}</span>
          {refusals > 0 ? `, ${refusals} refused by code` : ''}
        </Def>
        <Def label="Tokens">
          <span className="tnum">{run.input_tokens.toLocaleString('en-US')}</span> in · <span className="tnum">{run.output_tokens.toLocaleString('en-US')}</span> out ·{' '}
          <span className="tnum">{run.cache_read_tokens.toLocaleString('en-US')}</span> read from cache
        </Def>
        <Def label="Scope set by code">{Object.keys(run.scope ?? {}).length > 0 ? Object.entries(run.scope).map(([key, value]) => `${humanize(key).toLowerCase()} ${plainValue(value).slice(0, 12)}`).join(' · ') : 'None recorded'}</Def>
        <Def label="Run">
          <span className="ident">{run.id}</span>
        </Def>
      </dl>
      {run.error ? (
        <div className="border-t border-hairline-strong px-4 py-3">
          <h3 className="eyebrow mb-1">Why it stopped</h3>
          <p className="text-body text-pretty text-amber">{run.error}</p>
        </div>
      ) : null}
      <div className="border-t border-hairline-strong px-4 pt-3 pb-1">
        <h3 className="eyebrow mb-1">Steps, in order</h3>
        {run.steps.length === 0 ? (
          <p className="border-t border-ink py-2 text-body text-ink-700">No step was recorded: the run stopped before the model or a tool was called.</p>
        ) : (
          <ol className="border-t border-ink">
            {run.steps.map((step) => (
              <li key={step.id} className="grid grid-cols-[28px_minmax(0,1fr)_auto] gap-x-3 border-b border-hairline py-2 text-body last:border-b-0">
                <span className="tnum text-ink-500">{step.n}</span>
                <div className="min-w-0">
                  <p className="font-medium text-ink">
                    {STEP_KIND[step.kind] ?? humanize(step.kind)} · <span className="ident font-regular">{step.name}</span>
                  </p>
                  {step.input_summary ? (
                    <p className="mt-0.5 text-pretty break-words text-ink-700">
                      <span className="text-ink-500">In: </span>
                      {step.input_summary}
                    </p>
                  ) : null}
                  {step.output_summary ? (
                    <p className={cx('mt-0.5 text-pretty break-words', step.refused ? 'text-amber' : 'text-ink-700')}>
                      <span className="text-ink-500">{step.refused ? 'Refused: ' : 'Out: '}</span>
                      {step.output_summary}
                    </p>
                  ) : null}
                </div>
                <span className="text-right text-caption text-ink-500">
                  {step.refused ? <StatusDot tone="attention">Refused</StatusDot> : null}
                  {step.duration_ms !== null ? <span className="tnum block">{step.duration_ms.toLocaleString('en-US')} ms</span> : null}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
      {run.guardrail_notes.length > 0 ? (
        <div className="border-t border-hairline-strong px-4 pt-3 pb-3">
          <GuardrailNotes notes={run.guardrail_notes} as="h3" />
        </div>
      ) : (
        <p className="border-t border-hairline-strong px-4 py-3 text-body text-ink-700">No guardrail note was recorded for this run.</p>
      )}
      {run.output ? (
        <div className="border-t border-hairline-strong px-4 pt-3 pb-2">
          <h3 className="eyebrow mb-1">Answer after the guardrails</h3>
          <dl className="border-t border-ink">
            {Object.entries(run.output).map(([key, value]) => (
              <div key={key} className="grid grid-cols-[112px_minmax(0,1fr)] gap-x-4 border-b sm:grid-cols-[160px_minmax(0,1fr)] border-hairline py-1.5 text-body last:border-b-0">
                <dt className="text-ink-500">{humanize(key)}</dt>
                <dd className="text-pretty break-words whitespace-pre-line text-ink">{plainValue(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </Card>
  );
}

export function AgentActivity() {
  const runs = useAgentRuns();
  const search = useSearch({ from: '/agent-activity' });
  const navigate = useNavigate({ from: '/agent-activity' });
  const selectedId = search.run ?? runs.data?.[0]?.id ?? null;
  const detail = useAgentRun(selectedId);

  const columns = useMemo<Array<DataColumn<AgentRunRow>>>(
    () => [
      { id: 'when', header: 'Started, UTC', sortValue: (run) => run.created_at, cell: (run) => <span className="tnum text-ink-700">{formatTimestamp(run.created_at)}</span> },
      { id: 'agent', header: 'Agent', rowHeader: true, sortValue: (run) => run.agent_name, cell: (run) => <StatusDot tone="agent">{humanize(run.agent_name)}</StatusDot> },
      { id: 'task', header: 'Task', sortValue: (run) => run.task, cell: (run) => <span className="text-ink-700">{humanize(run.task)}</span> },
      { id: 'borrower', header: 'About', wrap: true, sortValue: (run) => run.borrower_name, cell: (run) => <span className="text-ink-700">{run.borrower_name ?? 'Portfolio'}</span> },
      { id: 'steps', header: 'Steps', align: 'right', sortValue: (run) => run.steps_count, cell: (run) => <span className="tnum">{run.steps_count}</span> },
      { id: 'notes', header: 'Guardrail notes', align: 'right', sortValue: (run) => run.guardrail_notes.length, cell: (run) => <span className="tnum">{run.guardrail_notes.length}</span> },
      {
        id: 'status',
        header: 'Outcome',
        sortValue: (run) => run.status,
        cell: (run) => {
          const status = STATUS[run.status] ?? { tone: 'neutral' as const, label: humanize(run.status) };
          return <StatusDot tone={status.tone} emphasis={status.tone === 'attention'}>{status.label}</StatusDot>;
        },
      },
    ],
    [],
  );

  return (
    <div data-ready={runs.data ? '' : undefined} className="space-y-5">
      <PageHeader eyebrow="Bank of Stoic · Commercial lending" title="Agent activity" meta={<span>Every run: what the agent was given, each model and tool step, what code refused, and what the guardrails changed</span>} />
      <Load query={runs} what="The agent runs" rows={10}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyCard
              title="No agent has run yet"
              description="The demonstration book was loaded from ground truth and replayed through the calculation code, so no model was called. A run appears here when an agent is asked to read a document, investigate a breach, draft commentary or answer a Copilot question."
            />
          ) : (
            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <section aria-label="Agent runs" className="min-w-0">
                <DataTable
                  caption="Agent runs, newest first"
                  data={rows}
                  columns={columns}
                  getRowId={(run) => run.id}
                  selectedRowId={selectedId}
                  onRowActivate={(run) => void navigate({ search: { run: run.id }, replace: true, resetScroll: false })}
                  stickyTop="var(--topbar-h)"
                  narrow="stack"
                  empty={<EmptyState title="No run" />}
                />
                <p className="mt-2 text-caption text-ink-500">Up and Down move between runs. Enter opens the run.</p>
              </section>
              <aside aria-label="Selected run" className="min-w-0 xl:sticky xl:top-[68px] xl:max-h-[calc(100vh-88px)] xl:overflow-y-auto xl:rounded-md">
                {detail.error ? <ErrorNotice error={detail.error} what="This run" onRetry={() => void detail.refetch()} /> : detail.data ? <RunDetail run={detail.data} /> : <SkeletonRows rows={8} label="Loading the run" />}
              </aside>
            </div>
          )
        }
      </Load>
    </div>
  );
}
