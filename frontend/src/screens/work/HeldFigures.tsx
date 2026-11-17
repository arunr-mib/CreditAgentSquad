import { useMemo, useState, type ReactNode } from 'react';
import { useConfirmFact, useCorrectFact, useCycles, useDocuments, useEnterFact, useFactsById, useSpread } from '@/api/hooks';
import type { FactChange, FactSummary, FootingProblem, HeldCell, SpreadContext, SpreadLineApi, WorkItemDetail } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { Button, formatFigure, ProvenanceGlyph, Select, StatusDot } from '@/design';
import { humanize, periodLabel, roleLabel, ROLES_WITH } from '@/domain/labels';
import { FigureForm, Refusal } from '@/repair/FigureForm';
import { RecalculationNote } from '@/repair/RecalculationNote';
import { useSource } from '@/source/context';
import { FactFigure, SourcedFigure } from '@/source/figures';

/* ── Reading the item's evidence ──────────────────────────────────────── */

const str = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);
const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value) && typeof value === 'object' && !Array.isArray(value);

/** The figures a spread held for a person, as the item's evidence lists them. Anything malformed is left out. */
export function heldCells(evidence: Record<string, unknown>): HeldCell[] {
  if (!Array.isArray(evidence.cells)) return [];
  return evidence.cells.filter(isRecord).flatMap((cell) => {
    const key = str(cell.key);
    if (!key) return [];
    return [
      {
        key,
        page: typeof cell.page === 'number' ? cell.page : null,
        printed_figure: str(cell.printed_figure),
        printed_label: str(cell.printed_label),
        row_label: str(cell.row_label),
        reason: str(cell.reason) ?? 'held',
        detail: str(cell.detail),
        fact_id: str(cell.fact_id),
      },
    ];
  });
}

/** The footing checks that failed, as the item's evidence lists them. */
export function footingProblems(evidence: Record<string, unknown>): FootingProblem[] {
  if (!Array.isArray(evidence.checks)) return [];
  return evidence.checks.filter(isRecord).flatMap((check) => {
    const code = str(check.code);
    if (!code) return [];
    const detail = isRecord(check.detail) ? { actual: str(check.detail.actual) ?? undefined, expected: str(check.detail.expected) ?? undefined, difference: str(check.detail.difference) ?? undefined } : null;
    return [{ key: str(check.key), code, message: str(check.message) ?? '', detail }];
  });
}

/** The period and units the spread was read in, when the item carries them. */
export function spreadContext(evidence: Record<string, unknown>): SpreadContext | null {
  const spread = isRecord(evidence.spread) ? evidence.spread : null;
  const periodEnd = spread ? str(spread.period_end) : null;
  if (!spread || !periodEnd || typeof spread.months !== 'number') return null;
  return { document_id: str(spread.document_id) ?? str(evidence.document_id), period_end: periodEnd, months: spread.months, scale: typeof spread.scale === 'number' ? spread.scale : undefined };
}

const STATED = 'stated.';
const COMPARATIVE = '@comparative';
const STATEMENT_LABEL: Record<string, string> = { is: 'Income statement', bs: 'Balance sheet', cf: 'Cash flow statement', sup: 'Supplemental' };

export interface LineDescription {
  /** The template line's key, without the printed-total prefix or the comparative suffix. */
  base: string;
  label: string;
  statement: string;
  /** "printed total" or "comparative column" when the held figure is not the line's own current figure. */
  qualifier: string | null;
  /** True when a person may key this line: an input line of the template, for the period itself. */
  input: boolean;
}

export function describeLine(key: string, lines: SpreadLineApi[]): LineDescription {
  const stated = key.startsWith(STATED);
  const comparative = key.endsWith(COMPARATIVE);
  const base = key.slice(stated ? STATED.length : 0, comparative ? key.length - COMPARATIVE.length : undefined);
  const line = lines.find((entry) => entry.key === base);
  const [prefix = '', ...rest] = base.split('.');
  return {
    base,
    label: line?.label ?? humanize(rest.join(' ') || base),
    statement: STATEMENT_LABEL[line?.statement ?? prefix] ?? humanize(prefix),
    qualifier: stated ? 'printed total' : comparative ? 'comparative column' : null,
    input: !stated && !comparative && (line ? !line.computed : true),
  };
}

const HOLD_REASON: Record<string, string> = {
  mapping_doubt: 'The row label is not a known name for this line',
  label_mismatch: 'The reported label was not found on the page',
  not_found: 'The figure was not found on the page',
  column_unconfirmed: 'The column could not be confirmed',
  ambiguous: 'The figure appears more than once on the page',
  unparseable: 'The printed figure could not be read as a number',
};
export const holdReason = (reason: string) => HOLD_REASON[reason] ?? humanize(reason);

const CHECK_FINDING: Record<string, string> = {
  missing_input: 'No figure is on file for this line',
  total_not_read: 'The printed total was not read',
  absent_not_verified: 'Not shown to be absent from the statement',
  does_not_foot: 'The lines do not add to the printed total',
  does_not_balance: 'Assets do not equal liabilities and equity',
  does_not_tie: 'The cash flow statement does not tie to the income statement',
  cash_roll_mismatch: 'The change in cash does not match the balance sheet',
};
export const checkFinding = (code: string) => CHECK_FINDING[code] ?? humanize(code);

/** What the two amounts of a failed comparison are. */
const COMPARED: Record<string, [string, string]> = {
  does_not_foot: ['Lines add to', 'Printed total'],
  does_not_balance: ['Total assets', 'Total liabilities and equity'],
  does_not_tie: ['Cash flow statement', 'Income statement'],
  cash_roll_mismatch: ['Net change in cash', 'Change in the cash balance'],
};

/* ── One line's repair: confirm, correct or key ───────────────────────── */

const cellClass = 'py-1.5 align-top';
const headClass = 'eyebrow border-b border-ink py-1 text-left font-semibold';

interface RepairProps {
  borrowerId: string;
  line: LineDescription;
  /** The fact the spread stored and held, if it stored one. */
  held?: FactSummary;
  heldId: string | null;
  /** The usable figure on file for the line and period now, when it is not the held fact itself. */
  current?: FactSummary;
  context: SpreadContext | null;
  /** The person's role may change figures and the item is still open. */
  canAct: boolean;
}

/** True while this line still needs a person: a held figure not yet cleared, or no figure at all. */
export function needsPerson(heldId: string | null, held: FactSummary | undefined, current: FactSummary | undefined): boolean {
  if (current) return false;
  if (!heldId) return true;
  return !held || held.status === 'proposed' || held.status === 'rejected';
}

function Repair({ borrowerId, line, held, heldId, current, context, canAct }: RepairProps) {
  const confirm = useConfirmFact();
  const correct = useCorrectFact();
  const enter = useEnterFact();
  const [mode, setMode] = useState<'correct' | 'key' | null>(null);
  const [result, setResult] = useState<FactChange | null>(null);

  const heldLive = held && (held.status === 'proposed' || held.status === 'verified' || held.status === 'confirmed') ? held : undefined;
  const target = heldLive ?? (current && current.kind !== 'calculated' ? current : undefined);
  const name = `${line.label}${line.qualifier ? `, ${line.qualifier}` : ''}`;
  // The row itself says what is on file now and what was recalculated; no toast repeats it.
  const done = (change: FactChange) => {
    setResult(change);
    setMode(null);
  };

  let status: ReactNode = null;
  if (heldLive?.status === 'confirmed') status = <StatusDot tone="pass">Confirmed by a person, as read</StatusDot>;
  else if (held?.status === 'rejected' && !current) status = <StatusDot tone="muted">Rejected; no figure is on file</StatusDot>;
  else if (current) {
    status = (
      <span className="inline-flex flex-wrap items-baseline gap-x-1.5">
        <StatusDot tone={current.kind === 'manual' ? 'pass' : 'neutral'}>{current.kind === 'manual' ? 'Entered by a person. On file now:' : 'On file now:'}</StatusDot>
        <FactFigure fact={current} weight="medium" />
      </span>
    );
  } else if (held?.status === 'superseded') status = <StatusDot tone="neutral">Superseded by a later figure</StatusDot>;

  // The held fact is still being read: nothing is offered until its state is known.
  const loading = Boolean(heldId) && !held;
  const cannotKey =
    !target && !current && !loading
      ? line.qualifier === 'printed total'
        ? 'A printed total cannot be keyed: totals are calculated by code from their lines. Key or correct the lines, or request a new document.'
        : line.qualifier === 'comparative column'
          ? 'A comparative-column figure cannot be keyed from here.'
          : !line.input
            ? 'This line is a total calculated by code; it cannot be keyed.'
            : !context
              ? 'The period of this spread is not recorded on the item, so a figure cannot be keyed from here.'
              : null
      : null;

  return (
    <div className="space-y-2">
      {status ? (
        <p className="text-body" data-repair-status>
          {status}
        </p>
      ) : null}
      {canAct && mode === null && !loading ? (
        <div className="flex flex-wrap items-center gap-1.5">
          {heldLive?.status === 'proposed' ? (
            <Button size="sm" disabled={confirm.isPending} aria-label={`Confirm ${name} as read`} onClick={() => confirm.mutate(heldLive.id)}>
              {confirm.isPending ? 'Confirming' : 'Confirm'}
            </Button>
          ) : null}
          {target ? (
            <Button size="sm" aria-label={`Correct ${name}`} onClick={() => (correct.reset(), setMode('correct'))}>
              Correct
            </Button>
          ) : null}
          {!target && !cannotKey ? (
            <Button size="sm" aria-label={`Key a figure for ${name}`} onClick={() => (enter.reset(), setMode('key'))}>
              Key a figure
            </Button>
          ) : null}
        </div>
      ) : null}
      {canAct && cannotKey ? <p className="text-caption text-pretty text-ink-500">{cannotKey}</p> : null}
      {confirm.error ? <Refusal error={confirm.error} /> : null}
      {mode === 'correct' && target ? (
        <FigureForm
          title={`Correct ${name}`}
          unit={target.unit}
          initialValue={target.value}
          scale={context?.scale}
          submitLabel="Record the correction"
          pendingLabel="Recording"
          pending={correct.isPending}
          error={correct.error}
          reasonHint="Recorded in the ledger with your name. The figure on file now is kept and marked superseded."
          onCancel={() => setMode(null)}
          onSubmit={({ value, reason }) => correct.mutate({ factId: target.id, value, reason }, { onSuccess: done })}
        />
      ) : null}
      {mode === 'key' && context ? (
        <FigureForm
          title={`Key ${name}, ${periodLabel(context.period_end, context.months).toLowerCase()}`}
          unit="usd"
          scale={context.scale}
          submitLabel="Record the figure"
          pendingLabel="Recording"
          pending={enter.isPending}
          error={enter.error}
          reasonHint="Recorded in the ledger with your name, as a figure entered by a person."
          onCancel={() => setMode(null)}
          onSubmit={({ value, reason }) => enter.mutate({ borrowerId, key: line.base, period_end: context.period_end, months: context.months, value, reason }, { onSuccess: done })}
        />
      ) : null}
      {result ? <RecalculationNote recalculation={result.recalculation} borrowerId={borrowerId} /> : null}
    </div>
  );
}

/* ── The figure as printed, opening the page it is on ─────────────────── */

function PrintedFigure({ cell, line, documentId, documentTitle, code }: { cell: HeldCell; line: LineDescription; documentId: string | null; documentTitle: string; code?: string }) {
  const source = useSource();
  if (!cell.printed_figure) return <span className="text-ink-500">Not read</span>;
  const figure = (
    <>
      <span className="tnum whitespace-nowrap">{cell.printed_figure}</span>
      <ProvenanceGlyph kind="extracted" />
    </>
  );
  const page = cell.page;
  if (!cell.fact_id && (!documentId || !page)) return <span className="inline-flex items-center gap-1 text-ink">{figure}</span>;
  return (
    <button
      type="button"
      data-printed-figure
      aria-label={`${cell.printed_figure}, ${line.label} as printed${page ? ` on page ${page}` : ''}. Read from a document. Show source.`}
      onClick={() =>
        cell.fact_id
          ? source.open({ type: 'fact', id: cell.fact_id })
          : source.open({ type: 'document', documentId: documentId as string, page: page as number, quote: cell.printed_figure, title: documentTitle, borrowerCode: code })
      }
      className="-mx-1 inline-flex items-center gap-1 rounded-xs px-1 text-ink t-colors hover:bg-cobalt-bg hover:text-cobalt-strong"
    >
      {figure}
    </button>
  );
}

/* ── Correct or key any line of the statement ─────────────────────────── */

function AnyLine({ borrowerId, lines, context, currentOf, suggested }: { borrowerId: string; lines: SpreadLineApi[]; context: SpreadContext; currentOf: (base: string) => FactSummary | undefined; suggested?: string }) {
  const inputs = lines.filter((line) => !line.computed);
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState(suggested && inputs.some((line) => line.key === suggested) ? suggested : (inputs[0]?.key ?? ''));
  if (inputs.length === 0) return null;
  if (!open) {
    return (
      <Button size="sm" onClick={() => setOpen(true)}>
        Correct or key another line
      </Button>
    );
  }
  const line = describeLine(key, lines);
  return (
    <div className="space-y-2 rounded-md border border-hairline bg-canvas px-3 py-2.5" data-any-line>
      <Select
        label={`Line of the statement, ${periodLabel(context.period_end, context.months).toLowerCase()}`}
        value={key}
        onValueChange={setKey}
        options={inputs.map((entry) => ({ value: entry.key, label: `${STATEMENT_LABEL[entry.statement] ?? humanize(entry.statement)} · ${entry.label}` }))}
      />
      {currentOf(key) ? null : <p className="text-caption text-ink-500">No figure is on file for this line and period.</p>}
      <Repair key={key} borrowerId={borrowerId} line={line} heldId={null} current={currentOf(key)} context={context} canAct />
    </div>
  );
}

/* ── The section on the work item ─────────────────────────────────────── */

/**
 * Repair of a held spread, on the work item itself: each held figure with the line it was filed
 * under, the row label code read from the page, the figure as printed and why it was held; and for
 * a spread that does not foot, each failed check. Every row can be confirmed, corrected or keyed
 * here; the decision that finishes the spread stays below, with the person.
 */
export function HeldFigures({ item, code, headingLevel: Heading = 'h3' }: { item: WorkItemDetail; code?: string; headingLevel?: 'h3' | 'h4' }) {
  const cells = useMemo(() => heldCells(item.evidence), [item.evidence]);
  const problems = useMemo(() => footingProblems(item.evidence), [item.evidence]);
  const doesNotFoot = item.item_type === 'spread.does_not_foot';
  const relevant = cells.length > 0 || doesNotFoot;
  const stated = useMemo(() => spreadContext(item.evidence), [item.evidence]);

  const { user, can } = useAuth();
  const spread = useSpread(relevant ? item.borrower_id : undefined);
  // An item that does not carry its period (a stand-in loaded with the book) takes it from its cycle.
  const cycles = useCycles({ borrower_id: item.borrower_id }, { enabled: relevant && !stated && Boolean(item.cycle_id) });
  const documents = useDocuments(relevant ? item.borrower_id : undefined);
  const cycle = !stated ? cycles.data?.find((row) => row.id === item.cycle_id) : undefined;
  const context: SpreadContext | null = stated ?? (cycle ? { document_id: str(item.evidence.document_id), period_end: cycle.period_end, months: cycle.months } : null);
  const lines = useMemo(() => spread.data?.lines ?? [], [spread.data]);

  const onFile = (base: string) => {
    const cell = context ? lines.find((line) => line.key === base)?.cells[context.period_end] : undefined;
    return cell?.usable ? cell.fact_id : null;
  };
  const rowKeys = [...cells.map((cell) => describeLine(cell.key, lines).base), ...problems.flatMap((problem) => (problem.key ? [describeLine(problem.key, lines).base] : []))];
  const facts = useFactsById([...cells.map((cell) => cell.fact_id), ...rowKeys.map(onFile), ...lines.filter((line) => !line.computed).map((line) => (doesNotFoot ? onFile(line.key) : null))]);
  const fact = (id: string | null) => (id ? facts.data?.[id] : undefined);
  const currentOf = (base: string, heldId: string | null = null) => {
    const id = onFile(base);
    return id && id !== heldId ? fact(id) : undefined;
  };

  if (!relevant) return null;

  const documentId = context?.document_id ?? str(item.evidence.document_id);
  const documentTitle = documents.data?.find((row) => row.id === documentId)?.title ?? 'Statement on file';
  const permitted = can(item.required_permission);
  const canAct = permitted && item.status === 'open';
  const waiting = cells.filter((cell) => needsPerson(cell.fact_id, fact(cell.fact_id), currentOf(describeLine(cell.key, lines).base, cell.fact_id))).length;
  const holders = (ROLES_WITH[item.required_permission] ?? []).map(roleLabel);

  return (
    <section aria-label="Held figures and their repair" data-held-figures className="space-y-3">
      {cells.length > 0 ? (
        <table className="w-full table-fixed text-body">
          <colgroup>
            <col className="w-[36%]" />
            <col />
            <col className="w-[22%]" />
          </colgroup>
          <caption className="pb-1 text-left">
            <Heading className="eyebrow inline">Held figures</Heading>
            <span className="ml-2 text-caption text-ink-500" aria-live="polite" data-held-count>
              {facts.isPending && cells.some((cell) => cell.fact_id) ? `${cells.length} held` : waiting === 0 ? `All ${cells.length} cleared; record the decision below` : `${waiting} of ${cells.length} still ${waiting === 1 ? 'needs' : 'need'} a person`}
            </span>
          </caption>
          <thead>
            <tr>
              <th scope="col" className={headClass}>
                Line
              </th>
              <th scope="col" className={headClass}>
                Row label on the page
              </th>
              <th scope="col" className={`${headClass} text-right`}>
                Printed
              </th>
            </tr>
          </thead>
          {cells.map((cell, index) => {
            const line = describeLine(cell.key, lines);
            const held = fact(cell.fact_id);
            return (
              <tbody key={`${cell.key}-${index}`} data-held-row={cell.key} className="border-b border-hairline last:border-b-0">
                <tr>
                  <th scope="row" className={`${cellClass} pr-3 text-left font-medium text-ink`}>
                    {line.label}
                    <span className="block text-caption font-regular text-ink-500">
                      {line.statement}
                      {line.qualifier ? `, ${line.qualifier}` : ''}
                    </span>
                  </th>
                  <td className={`${cellClass} pr-3 text-ink-700`}>
                    {cell.row_label ? (
                      cell.row_label
                    ) : (
                      <>
                        <span className="text-ink-500">No label read</span>
                        {cell.printed_label ? <span className="block text-caption text-ink-500">The reader reported “{cell.printed_label}”</span> : null}
                      </>
                    )}
                  </td>
                  <td className={`${cellClass} text-right`}>
                    <PrintedFigure cell={cell} line={line} documentId={documentId} documentTitle={documentTitle} code={code} />
                    {cell.page ? <span className="tnum block text-caption text-ink-500">page {cell.page}</span> : null}
                  </td>
                </tr>
                <tr>
                  <td colSpan={3} className="pb-2.5">
                    <p className="text-body">
                      <StatusDot tone={needsPerson(cell.fact_id, held, currentOf(line.base, cell.fact_id)) ? 'attention' : 'muted'}>Held: {holdReason(cell.reason).toLowerCase()}</StatusDot>
                    </p>
                    {cell.detail ? <p className="mb-1.5 pl-[13px] text-caption text-pretty text-ink-500">{cell.detail}</p> : null}
                    <div className="pl-[13px]">
                      <Repair borrowerId={item.borrower_id} line={line} held={held} heldId={cell.fact_id} current={currentOf(line.base, cell.fact_id)} context={context} canAct={canAct} />
                    </div>
                  </td>
                </tr>
              </tbody>
            );
          })}
        </table>
      ) : null}

      {problems.length > 0 ? (
        <table className="w-full text-body">
          <caption className="pb-1 text-left">
            <Heading className="eyebrow inline">Checks that failed</Heading>
            <span className="ml-2 text-caption text-ink-500">{problems.length} on this statement</span>
          </caption>
          <thead>
            <tr>
              <th scope="col" className={headClass}>
                Line
              </th>
              <th scope="col" className={headClass}>
                What the check found
              </th>
            </tr>
          </thead>
          <tbody>
            {problems.map((problem, index) => {
              const line = problem.key ? describeLine(problem.key, lines) : null;
              const compared = COMPARED[problem.code];
              const detail = problem.detail;
              const amounts = compared && detail?.actual && detail.expected ? ([[compared[0], detail.actual], [compared[1], detail.expected], ...(detail.difference ? [['Difference', detail.difference] as [string, string]] : [])] as Array<[string, string]>) : null;
              return (
                <tr key={`${problem.code}-${problem.key}-${index}`} data-check-row={problem.key ?? problem.code} className="border-b border-hairline last:border-b-0">
                  <th scope="row" className={`${cellClass} w-[42%] pr-3 text-left font-medium text-ink`}>
                    {line ? line.label : 'The statement'}
                    {line ? <span className="block text-caption font-regular text-ink-500">{line.statement}</span> : null}
                  </th>
                  <td className={cellClass}>
                    <p className="text-pretty text-ink-700">{checkFinding(problem.code)}</p>
                    {amounts ? (
                      <dl className="mt-0.5 text-caption text-ink-700">
                        {amounts.map(([label, value]) => (
                          <div key={label} className="flex items-baseline justify-between gap-3">
                            <dt className="text-ink-500">{label}</dt>
                            <dd>
                              <SourcedFigure
                                value={value}
                                unit="usd"
                                kind="calculated"
                                label={`${label}, ${line?.label ?? 'the statement'}`}
                                source={{
                                  type: 'record',
                                  kind: 'calculated',
                                  title: checkFinding(problem.code),
                                  value: formatFigure(value, 'usd').text,
                                  rows: amounts.map(([name, amount]) => [name, formatFigure(amount, 'usd').text]),
                                  note: 'Worked out by the statement checks from the figures on file for the period. Each line of the statement opens its own source on the Spreads tab.',
                                  link: code ? { to: `/borrowers/${code}/spreads`, label: 'Open the spread' } : undefined,
                                }}
                              />
                            </dd>
                          </div>
                        ))}
                      </dl>
                    ) : problem.message && !CHECK_FINDING[problem.code] ? (
                      <p className="text-caption text-pretty text-ink-500">{problem.message}</p>
                    ) : null}
                    {line?.input && problem.code === 'missing_input' ? (
                      <div className="mt-1.5">
                        <Repair borrowerId={item.borrower_id} line={line} heldId={null} current={currentOf(line.base)} context={context} canAct={canAct} />
                      </div>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}

      {doesNotFoot && cells.length === 0 && problems.length === 0 ? (
        <p className="text-body text-pretty text-ink-700">This item does not list the figures or checks behind it. A line can still be corrected or keyed for the period below.</p>
      ) : null}
      {doesNotFoot && canAct && context ? (
        <AnyLine borrowerId={item.borrower_id} lines={lines} context={context} currentOf={(base) => currentOf(base)} suggested={problems.find((problem) => problem.key)?.key ?? undefined} />
      ) : null}
      {!permitted && item.status === 'open' && user ? (
        <p className="text-caption text-pretty text-ink-700">
          Confirming, correcting and keying figures needs {holders.length > 0 ? `a ${holders.join(' or a ').toLowerCase()}` : 'another role'}. Your role, {roleLabel(user.role)}, can read the held
          figures and open their pages.
        </p>
      ) : null}
    </section>
  );
}
