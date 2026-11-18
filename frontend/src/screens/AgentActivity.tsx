import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { Ban, Check, MessageSquareText, PenLine, Play, ShieldCheck, StickyNote, Wrench } from 'lucide-react';
import { useMemo, useRef, useSyncExternalStore, type KeyboardEvent, type ReactNode } from 'react';
import { useAgentRun, useAgentRuns, useAgentsStatus } from '@/api/hooks';
import type { AgentRunDetail, AgentRunRow, AgentStepRow } from '@/api/schema';
import { AgentMark, Button, Card, formatDate, GuardrailNotes, Kbd, PageHeader, SkeletonRows, StatusDot, Tag } from '@/design';
import { useWorkspaceDrawer } from '@/drawer/context';
import { formatTimestamp, humanize } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { AgentBody, referencedFactIds } from '@/source/AgentBody';
import { Def, ErrorNotice, Load, Notice } from './parts';

/* ── Words ────────────────────────────────────────────────────────────── */

/** The task an agent was given, as a person would say it. A task this list does not know is shown in its own words. */
const TASK: Record<string, string> = {
  classify_documents: 'Classify the documents received',
  spread_statements: 'Spread the financial statements',
  read_certificate: 'Read the compliance certificate',
  read_borrowing_base: 'Read the borrowing base certificate',
  extract_terms: 'Read the terms from the loan documents',
  investigate_covenant_exception: 'Investigate a covenant exception',
  explain_signals: 'Explain the early warning signals',
  draft_review_commentary: 'Draft the review commentary',
  answer_question: 'Answer a question put to the Copilot',
};
export const taskLabel = (task: string) => TASK[task] ?? humanize(task);
/** An agent's name in words. A name recorded with its version ("review@1") is the same agent. */
export const agentLabel = (recorded: string) => {
  const name = recorded.split('@')[0] ?? recorded;
  return name === 'copilot' ? 'Copilot' : `${humanize(name)} agent`;
};

const STATUS_LABEL: Record<string, string> = { running: 'Running', completed: 'Completed', abstained: 'Abstained', failed: 'Failed', refused: 'Refused' };
const STEP_KIND: Record<string, string> = { model: 'Model call', tool: 'Tool call', guardrail: 'Guardrail', note: 'Note' };
const count = (value: number) => value.toLocaleString('en-US');

/** "840 ms", "12.4 s", "2 min 05 s". The duration itself comes from the server; this only sets it in a readable unit. */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${count(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)} min ${String(seconds % 60).padStart(2, '0')} s`;
}

const isSet = (value: unknown): boolean =>
  value !== null && value !== undefined && value !== '' && !(Array.isArray(value) && value.length === 0) && !(typeof value === 'object' && !Array.isArray(value) && Object.keys(value as object).length === 0);

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** One scope value in plain words: dates as dates, ids as their first eight characters, lists joined. */
function scopeValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(scopeValue).join(', ');
  if (typeof value === 'string') return UUID.test(value) ? value.slice(0, 8) : ISO_DATE.test(value) ? formatDate(value) : value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return Object.entries(value as Record<string, unknown>)
    .filter(([, inner]) => isSet(inner))
    .map(([key, inner]) => `${humanize(key).toLowerCase()} ${scopeValue(inner)}`)
    .join(', ');
}

/**
 * The scope code set for the run, in plain words. Only the fields that were set: an empty list or a
 * missing facility says nothing, so it is left out. A borrower is named when the run names it.
 */
export function scopeParts(scope: Record<string, unknown> | null | undefined, run?: Pick<AgentRunRow, 'borrower_id' | 'borrower_name'>): string[] {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(scope ?? {})) {
    if (!isSet(value)) continue;
    const name = humanize(key.replace(/_ids?$/, '')).toLowerCase();
    if (key === 'borrower_id' && run?.borrower_name && value === run.borrower_id) parts.push(`borrower ${run.borrower_name}`);
    else if (key === 'months' && typeof value === 'number') parts.push(`${value} months`);
    else if (key === 'period_end' && typeof value === 'string') parts.push(`period ended ${scopeValue(value)}`);
    else if (key.endsWith('_ids') && Array.isArray(value)) parts.push(`${value.length === 1 ? name : `${name}s`} ${scopeValue(value)}`);
    else parts.push(`${name} ${scopeValue(value)}`);
  }
  return parts;
}

/* ── The answer, as fields ────────────────────────────────────────────── */

const TITLE_KEYS = ['heading', 'title', 'name'];

/** Agent text: each {{fact:…}} becomes a figure chip that opens its source. */
function OutputText({ text }: { text: string }) {
  if (referencedFactIds(text).length === 0) return <span className="whitespace-pre-line">{text}</span>;
  return <AgentBody text={text} chips className="text-body" />;
}

/** Structured output as labelled fields, never as raw JSON. */
export function OutputValue({ value, depth = 0 }: { value: unknown; depth?: number }): ReactNode {
  if (!isSet(value)) return <span className="text-ink-500">None</span>;
  if (typeof value === 'string') return <OutputText text={value} />;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return String(value);
  if (Array.isArray(value)) {
    if (value.every((entry) => typeof entry !== 'object' || entry === null)) {
      return (
        <ul className="list-disc space-y-0.5 pl-4">
          {value.map((entry, index) => (
            <li key={index}>
              <OutputValue value={entry} depth={depth + 1} />
            </li>
          ))}
        </ul>
      );
    }
    return (
      <ol className="space-y-2">
        {value.map((entry, index) => (
          <li key={index} data-output-item className="rounded-sm border border-hairline px-3 py-2">
            <OutputValue value={entry} depth={depth + 1} />
          </li>
        ))}
      </ol>
    );
  }
  const record = value as Record<string, unknown>;
  const titleKey = TITLE_KEYS.find((key) => typeof record[key] === 'string' && record[key]);
  // Under a heading, the section's machine key says nothing a reader needs.
  const fields = Object.entries(record).filter(([key]) => key !== titleKey && !(titleKey && key === 'key'));
  return (
    <div>
      {titleKey ? <p className="mb-1 font-semibold text-ink">{String(record[titleKey])}</p> : null}
      <dl className="space-y-1.5">
        {fields.map(([key, inner]) => (
          <div key={key}>
            <dt className="eyebrow">{humanize(key)}</dt>
            <dd className="mt-0.5 text-ink">
              <OutputValue value={inner} depth={depth + 1} />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/* ── Guardrail marks ──────────────────────────────────────────────────── */

export type CheckResult = 'passed' | 'changed' | 'blocked';

const PASSED = new Set(['passed', 'pass']);
/** The check stopped the answer: nothing of it went on. Every other action changed or flagged something and let the rest through. */
const BLOCKED = new Set(['blocked', 'refuse', 'refused', 'abstain', 'no_draft', 'nothing_stored']);
const RESULT_WORD: Record<string, string> = {
  passed: 'passed',
  pass: 'passed',
  changed: 'changed',
  blocked: 'blocked',
  refuse: 'refused',
  refused: 'refused',
  abstain: 'abstained',
  retry: 'retried',
  escalate: 'escalated',
};

export function checkResult(action: string): CheckResult {
  return PASSED.has(action) ? 'passed' : BLOCKED.has(action) ? 'blocked' : 'changed';
}

export interface CheckMark {
  key: string;
  check: string;
  /** The action as the run recorded it. */
  action: string;
  result: CheckResult;
  /** How many times the record names this check with this action. */
  times: number;
}

/**
 * One mark per guardrail check the run's own record names, with the result recorded there. Nothing is
 * inferred: a run with no notes gets no marks, and a check is never shown as passed unless the record says so.
 */
export function checkMarks(notes: ReadonlyArray<{ check: string; action: string }> | null | undefined): CheckMark[] {
  const marks = new Map<string, CheckMark>();
  for (const note of notes ?? []) {
    if (!note || typeof note.check !== 'string' || typeof note.action !== 'string') continue;
    const key = `${note.check}:${note.action}`;
    const seen = marks.get(key);
    if (seen) seen.times += 1;
    else marks.set(key, { key, check: note.check, action: note.action, result: checkResult(note.action), times: 1 });
  }
  return [...marks.values()];
}

const RESULT_ICON = { passed: Check, changed: PenLine, blocked: Ban } as const;

function CheckMarks({ notes }: { notes: AgentRunRow['guardrail_notes'] }) {
  const marks = checkMarks(notes as ReadonlyArray<{ check: string; action: string }>);
  if (marks.length === 0) return <p className="text-caption text-ink-500">No guardrail check is named on this run’s record.</p>;
  return (
    <ul aria-label="Guardrail checks named on the run’s record" className="flex flex-wrap gap-x-4 gap-y-1">
      {marks.map((mark) => {
        const Icon = RESULT_ICON[mark.result];
        const passed = mark.result === 'passed';
        return (
          <li key={mark.key} data-check={mark.check} data-result={mark.result} className="inline-flex items-center gap-1 text-caption text-ink-700">
            <Icon size={12} strokeWidth={2.5} aria-hidden className={cx('shrink-0', passed ? 'text-green-mark' : 'text-amber-mark')} />
            <span>{humanize(mark.check)}:</span>{' '}
            <span className={cx('font-medium', passed ? 'text-green' : 'text-amber')}>{RESULT_WORD[mark.action] ?? humanize(mark.action).toLowerCase()}</span>
            {mark.times > 1 ? (
              <>
                {' '}
                <span className="tnum text-ink-500">×{mark.times}</span>
              </>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

/* ── One run ──────────────────────────────────────────────────────────── */

/** A tag only for a run that failed or was refused: those need a person. Every other state is plain text. */
function RunStatus({ status }: { status: string }) {
  const label = STATUS_LABEL[status] ?? humanize(status);
  if (status === 'failed' || status === 'refused') return <Tag tone="attention">{label}</Tag>;
  if (status === 'running') return <StatusDot tone="agent">{label}</StatusDot>;
  return <span className="text-ink-500">{label}</span>;
}

function About({ run, className }: { run: AgentRunRow; className?: string }) {
  return (
    <p className={cx('text-body text-pretty text-ink-700', className)}>
      {run.borrower_name ? (
        run.borrower_code ? (
          <Link to="/borrowers/$code" params={{ code: run.borrower_code }} className="link relative z-[1]">
            {run.borrower_name}
          </Link>
        ) : (
          run.borrower_name
        )
      ) : (
        'No single borrower'
      )}
      {run.period_end ? ` · period ended ${formatDate(run.period_end)}` : ''}
    </p>
  );
}

/** Duration, tokens and model, as the run recorded them. Mono: these are a machine's readings, not credit figures. */
function Telemetry({ run }: { run: AgentRunRow }) {
  const parts = [
    run.duration_ms !== null && run.duration_ms !== undefined ? formatDuration(run.duration_ms) : null,
    `${count(run.input_tokens)} in`,
    `${count(run.output_tokens)} out`,
    run.served_model ?? run.model,
  ].filter((part): part is string => Boolean(part));
  // Lines break between readings, never inside one: a model id stays whole on a phone.
  return (
    <p data-telemetry className="ident text-caption text-ink-500">
      {parts.map((part, index) => (
        <span key={index} className="whitespace-nowrap">
          {index > 0 ? ' · ' : ''}
          {part}
        </span>
      ))}
    </p>
  );
}

function RunRow({ run, selected, onSelect, children }: { run: AgentRunRow; selected: boolean; onSelect: (id: string) => void; children?: ReactNode }) {
  const time = run.created_at.slice(11, 16);
  return (
    <li data-run={run.id} data-status={run.status} className="border-b border-hairline last:border-b-0">
      <div
        className={cx(
          'relative grid grid-cols-[20px_minmax(0,1fr)] gap-x-2.5 px-3 py-3 t-colors sm:grid-cols-[40px_20px_minmax(0,1fr)] sm:px-4',
          // the selected-row bar: 3 px of cobalt on the left edge and a warm tint
          selected ? 'bg-hover before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:bg-cobalt' : 'bg-surface hover:bg-hover',
        )}
      >
        {/* the rail the agent marks sit on */}
        <span aria-hidden className="absolute inset-y-0 left-[21.5px] w-px bg-hairline-strong sm:left-[75.5px]" />
        <time dateTime={run.created_at} className="tnum pt-px text-caption text-ink-500 max-sm:hidden">
          {time}
        </time>
        <span className="relative z-[1] flex h-5 items-center justify-center bg-[inherit]">
          <AgentMark />
        </span>
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5 text-caption">
            <p className="font-semibold text-iris">
              {agentLabel(run.agent_name)} <span className="ident font-regular text-ink-500">v{run.agent_version}</span>
              <time dateTime={run.created_at} className="tnum ml-2 font-regular text-ink-500 sm:hidden">
                {time}
              </time>
            </p>
            <RunStatus status={run.status} />
          </div>
          <h3 className="text-body font-medium text-ink">
            <button
              type="button"
              data-run-button
              aria-pressed={selected}
              onClick={() => onSelect(run.id)}
              className="text-left text-pretty after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:-outline-offset-2 focus-visible:after:outline-cobalt"
            >
              {taskLabel(run.task)}
            </button>
          </h3>
          <About run={run} />
          <CheckMarks notes={run.guardrail_notes} />
          <Telemetry run={run} />
        </div>
      </div>
      {children}
    </li>
  );
}

/* ── The timeline ─────────────────────────────────────────────────────── */

const weekday = (day: string) => new Date(`${day}T00:00:00Z`).toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' });

function byDay(runs: AgentRunRow[]): Array<{ day: string; runs: AgentRunRow[] }> {
  const days = new Map<string, AgentRunRow[]>();
  for (const run of [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at))) {
    const day = run.created_at.slice(0, 10);
    days.set(day, [...(days.get(day) ?? []), run]);
  }
  return [...days].map(([day, list]) => ({ day, runs: list }));
}

export interface RunTimelineProps {
  runs: AgentRunRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** On a narrow screen the selected run's steps open under its row. */
  inline?: (run: AgentRunRow) => ReactNode;
}

/** Runs newest first, grouped by day (UTC, as the ledger records time). J, K and the arrow keys move between runs. */
export function RunTimeline({ runs, selectedId, onSelect, inline }: RunTimelineProps) {
  const days = useMemo(() => byDay(runs), [runs]);
  const ref = useRef<HTMLDivElement>(null);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.key === 'ArrowDown' || event.key === 'j' ? 1 : event.key === 'ArrowUp' || event.key === 'k' ? -1 : 0;
    if (step === 0 || event.metaKey || event.ctrlKey || event.altKey) return;
    const buttons = [...(ref.current?.querySelectorAll<HTMLButtonElement>('[data-run-button]') ?? [])];
    const next = buttons[buttons.indexOf(document.activeElement as HTMLButtonElement) + step];
    if (!next) return;
    event.preventDefault();
    next.focus();
    next.click();
  }

  return (
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions -- the keys act on the row buttons inside, which carry the roles
    <div ref={ref} onKeyDown={onKeyDown} className="space-y-5">
      {days.map((group) => (
        <section key={group.day} aria-label={`Runs on ${formatDate(group.day)}`}>
          <h2 className="mb-1.5 flex items-baseline justify-between gap-3 px-1">
            <span className="text-body font-semibold text-ink">
              {weekday(group.day)} <span className="tnum">{formatDate(group.day)}</span>
            </span>
            <span className="tnum text-caption text-ink-500">
              {group.runs.length} {group.runs.length === 1 ? 'run' : 'runs'}
            </span>
          </h2>
          <Card className="overflow-hidden">
            <ol>
              {group.runs.map((run) => (
                <RunRow key={run.id} run={run} selected={run.id === selectedId} onSelect={onSelect}>
                  {inline && run.id === selectedId ? inline(run) : null}
                </RunRow>
              ))}
            </ol>
          </Card>
        </section>
      ))}
    </div>
  );
}

/* ── The selected run: what it read, called and was checked for ───────── */

const STEP_ICON: Record<string, typeof Wrench> = { tool: Wrench, guardrail: ShieldCheck, note: StickyNote };

function StepMark({ kind }: { kind: AgentStepRow['kind'] }) {
  if (kind === 'model') return <AgentMark className="mt-[5px]" />;
  const Icon = STEP_ICON[kind];
  return Icon ? <Icon size={13} aria-hidden className="mt-[3px] shrink-0 text-ink-500" /> : <span aria-hidden className="mt-[3px] size-[13px]" />;
}

export function RunDetail({ run, flush }: { run: AgentRunDetail; flush?: boolean }) {
  const refusals = run.steps.filter((step) => step.refused).length;
  const scope = scopeParts(run.scope, run);
  const body = (
    <>
      {flush ? null : (
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 px-4 pt-3.5 pb-3">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-1.5 text-caption font-semibold text-iris">
              <AgentMark />
              {agentLabel(run.agent_name)} <span className="ident font-regular text-ink-500">v{run.agent_version}</span>
            </p>
            <h2 className="text-title font-semibold text-pretty text-ink">{taskLabel(run.task)}</h2>
            <About run={run} className="mt-0.5" />
          </div>
          <span className="text-body">
            <RunStatus status={run.status} />
          </span>
        </div>
      )}
      <dl className={cx('px-4 pb-1', !flush && 'border-t border-hairline')}>
        <Def label="Started">
          <span className="tnum">{formatTimestamp(run.created_at)}</span> UTC
        </Def>
        <Def label="Model">
          <span className="ident whitespace-nowrap">{run.served_model ?? run.model}</span> · {run.llm_mode} responses
        </Def>
        {run.duration_ms !== null && run.duration_ms !== undefined ? (
          <Def label="Duration">
            <span className="ident">{formatDuration(run.duration_ms)}</span>
          </Def>
        ) : null}
        <Def label="Tokens">
          <span className="ident">
            {count(run.input_tokens)} in · {count(run.output_tokens)} out · {count(run.cache_read_tokens)} read from cache
          </span>
        </Def>
        <Def label="Steps">
          {/* The steps listed below are the record; the summary count on the run row can lag behind them. */}
          <span className="tnum">{run.steps.length}</span>
          {refusals > 0 ? `, ${refusals} refused by code` : ''}
        </Def>
        <Def label="Scope set by code">{scope.length > 0 ? scope.join(' · ') : 'None recorded'}</Def>
        <Def label="Run">
          <span className="ident [overflow-wrap:anywhere]">{run.id}</span>
        </Def>
      </dl>
      {run.error ? (
        <div className="border-t border-hairline-strong px-4 py-3">
          <h3 className="eyebrow mb-1">Why it stopped</h3>
          <p className="text-body text-pretty text-amber [overflow-wrap:anywhere]">{run.error}</p>
        </div>
      ) : null}
      <div className="border-t border-hairline-strong px-4 pt-3 pb-1">
        <h3 className="eyebrow mb-1">Steps, in order</h3>
        {run.steps.length === 0 ? (
          <p className="border-t border-ink py-2 text-body text-ink-700">No step was recorded: the run stopped before the model or a tool was called.</p>
        ) : (
          <ol className="border-t border-ink">
            {run.steps.map((step) => (
              <li key={step.id} className="grid grid-cols-[20px_14px_minmax(0,1fr)] gap-x-2 border-b border-hairline py-2 text-body last:border-b-0 sm:grid-cols-[20px_14px_minmax(0,1fr)_auto]">
                <span className="tnum text-ink-500">{step.n}</span>
                <StepMark kind={step.kind} />
                <div className="min-w-0">
                  <p className="font-medium text-ink">
                    {STEP_KIND[step.kind] ?? humanize(step.kind)} · <span className="ident font-regular">{step.name}</span>
                  </p>
                  {step.input_summary ? (
                    <p className="mt-0.5 text-pretty text-ink-700 [overflow-wrap:anywhere]">
                      <span className="text-ink-500">In: </span>
                      {step.input_summary}
                    </p>
                  ) : null}
                  {step.output_summary ? (
                    <p className={cx('mt-0.5 text-pretty [overflow-wrap:anywhere]', step.refused ? 'text-amber' : 'text-ink-700')}>
                      <span className="text-ink-500">{step.refused ? 'Refused: ' : 'Out: '}</span>
                      {step.output_summary}
                    </p>
                  ) : null}
                </div>
                <span className="text-caption text-ink-500 max-sm:col-start-3 sm:text-right">
                  {step.refused ? <StatusDot tone="attention">Refused</StatusDot> : null}
                  {step.duration_ms !== null ? <span className="ident block">{count(step.duration_ms)} ms</span> : null}
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
        <p className="border-t border-hairline-strong px-4 py-3 text-body text-ink-700">No guardrail check is named on this run’s record.</p>
      )}
      {run.output ? (
        <div className="border-t border-hairline-strong px-4 pt-3 pb-2">
          <h3 className="eyebrow mb-1">Answer after the guardrails</h3>
          <dl data-run-output className="border-t border-ink">
            {Object.entries(run.output).map(([key, value]) => (
              <div key={key} className="border-b border-hairline py-2 text-body last:border-b-0">
                <dt className="mb-1 text-ink-500">{humanize(key)}</dt>
                <dd className="min-w-0 text-pretty text-ink [overflow-wrap:break-word]">
                  <OutputValue value={value} />
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </>
  );
  return flush ? (
    <div data-agent-run={run.id} className="border-t border-hairline-strong bg-surface">
      {body}
    </div>
  ) : (
    <Card data-agent-run={run.id}>{body}</Card>
  );
}

function SelectedRun({ id, flush }: { id: string; flush?: boolean }) {
  const detail = useAgentRun(id);
  if (detail.error) return <ErrorNotice error={detail.error} what="This run" onRetry={() => void detail.refetch()} />;
  if (!detail.data) return <SkeletonRows rows={8} label="Loading the run" />;
  return <RunDetail run={detail.data} flush={flush} />;
}

/* ── When nothing has run ─────────────────────────────────────────────── */

/** Says how a run starts, what it costs, and whether one can start here at all. */
export function HowRunsStart({ connected }: { connected: boolean | undefined }) {
  const { openCopilot } = useWorkspaceDrawer();
  return (
    <Card>
      <div className="px-4 pt-4 pb-3 sm:px-6 sm:pt-5">
        <h2 className="text-title font-semibold text-ink">No agent has run yet</h2>
        <p className="mt-1 max-w-[68ch] text-prose text-pretty text-ink-700">
          The demonstration book was loaded from the synthetic book and replayed through the calculation code, so no model was called. A run appears here
          as soon as an agent is given a task. There are two ways to start one.
        </p>
      </div>
      <ul className="grid border-t border-hairline md:grid-cols-2 md:divide-x md:divide-hairline max-md:divide-y max-md:divide-hairline">
        <li className="flex flex-col items-start gap-1 px-4 py-4 sm:px-6">
          <Play size={16} aria-hidden className="mb-1 text-ink-500" />
          <h3 className="text-body font-semibold text-ink">Run a stage of a borrower’s cycle</h3>
          <p className="max-w-[52ch] text-body text-pretty text-ink-700">
            Open a borrower and choose “Run … now” beside its monitoring cycle. The button names the stage it will run, and the stage’s agents read the
            documents on file.
          </p>
          <Link to="/borrowers" className="link mt-1 text-body font-medium">
            Choose a borrower
          </Link>
        </li>
        <li className="flex flex-col items-start gap-1 px-4 py-4 sm:px-6">
          <MessageSquareText size={16} aria-hidden className="mb-1 text-ink-500" />
          <h3 className="text-body font-semibold text-ink">Ask the Copilot a question</h3>
          <p className="max-w-[52ch] text-body text-pretty text-ink-700">
            Each question is one run. The answer is read-only: it is checked against stored facts and verified pages, and it changes nothing.
          </p>
          <Button size="sm" className="mt-1.5" disabled={connected === false} onClick={() => openCopilot()} iconRight={<Kbd>Ctrl J</Kbd>}>
            Ask the Copilot
          </Button>
        </li>
      </ul>
      <p className="border-t border-hairline px-4 py-3 text-body text-pretty text-ink-700 sm:px-6">
        <span className="font-medium text-ink">Each run is billable.</span> It calls a model, and it is recorded in the ledger in the name of the person
        who started it.
      </p>
    </Card>
  );
}

function useIsWide(): boolean {
  const query = '(min-width: 1400px)'; // the xl breakpoint: two-column work layouts
  return useSyncExternalStore(
    (changed) => {
      const media = window.matchMedia?.(query);
      media?.addEventListener('change', changed);
      return () => media?.removeEventListener('change', changed);
    },
    () => window.matchMedia?.(query).matches ?? true,
    () => true,
  );
}

/* ── The screen ───────────────────────────────────────────────────────── */

export function AgentActivity() {
  const runs = useAgentRuns();
  const status = useAgentsStatus();
  const search = useSearch({ from: '/agent-activity' });
  const navigate = useNavigate({ from: '/agent-activity' });
  const wide = useIsWide();
  // Beside the timeline the newest run is shown until another is chosen. Under a row, nothing opens until it is asked for.
  const selectedId = search.run ?? (wide ? (runs.data?.[0]?.id ?? null) : null);
  const select = (id: string) => void navigate({ search: { run: !wide && id === search.run ? undefined : id }, replace: true, resetScroll: false });
  const connected = status.data?.model_connected;

  return (
    <div data-ready={runs.data ? '' : undefined} className="space-y-5">
      <PageHeader
        eyebrow="Bank of Stoic · Commercial lending"
        title="Agent activity"
        meta={<span>Every run: the task an agent was given, the guardrail checks its record names, and what it took in time and tokens</span>}
        actions={
          status.data ? (
            <p data-model-status className="flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-ink-700">
              <span className="text-ink-500">Model</span>
              <span className="ident text-ink">{status.data.model}</span>
              <span>
                {status.data.mode} responses{connected ? ', connected' : ''}
              </span>
            </p>
          ) : null
        }
      />
      {status.data && !connected ? (
        <Notice tone="attention" title="Agents cannot run on this deployment">
          {status.data.reason} “Run … now” on a borrower’s cycle and the Copilot stay switched off until a model is connected.
        </Notice>
      ) : null}
      <Load query={runs} what="The agent runs" rows={10}>
        {(rows) =>
          rows.length === 0 ? (
            <HowRunsStart connected={connected} />
          ) : (
            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
              <section aria-label="Agent runs, newest first" className="min-w-0">
                <RunTimeline runs={rows} selectedId={selectedId} onSelect={select} inline={wide ? undefined : (run) => <SelectedRun id={run.id} flush />} />
                <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 px-1 text-caption text-ink-500">
                  <span className="inline-flex items-center gap-1">
                    <Kbd>J</Kbd>
                    <Kbd>K</Kbd> move between runs
                  </span>
                  <span>Times are UTC</span>
                  <span>A mark is shown only for a check the run’s record names</span>
                </p>
              </section>
              {wide ? (
                <aside aria-label="Selected run" className="min-w-0 xl:sticky xl:top-[68px] xl:max-h-[calc(100vh-88px)] xl:overflow-y-auto xl:rounded-md">
                  {selectedId ? <SelectedRun key={selectedId} id={selectedId} /> : null}
                </aside>
              ) : null}
            </div>
          )
        }
      </Load>
    </div>
  );
}
