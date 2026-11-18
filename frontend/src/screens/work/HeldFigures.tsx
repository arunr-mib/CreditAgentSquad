import { useId, useMemo, useState, type ReactNode } from 'react';
import { useConfirmFact, useCorrectFact, useCycles, useDocuments, useEnterFact, useFactsById, useRejectFact, useSpread } from '@/api/hooks';
import type { FactSummary, HeldCell, Recalculation, SpreadContext, SpreadLineApi, WorkItemDetail } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { Button, formatDate, formatFigure, ProvenanceGlyph, Select, StatusDot } from '@/design';
import { humanize, roleLabel, ROLES_WITH } from '@/domain/labels';
import { FigureForm, Refusal } from '@/repair/FigureForm';
import {
  checkFinding,
  COMPARED,
  describeLine,
  footingProblems,
  heldCells,
  knownCheck,
  needsPerson,
  periodPhrase,
  primaryAction,
  spreadContext,
  STATEMENT_LABEL,
  str,
  swappedPairs,
  whatCodeWillDo,
  whyHeld,
  type LineDescription,
  type Primary,
} from '@/repair/held';
import { RecalculationNote } from '@/repair/RecalculationNote';
import { useSource } from '@/source/context';
import { FactFigure, SourcedFigure } from '@/source/figures';

/** One thing code did after a click, as the API reported it. An action that makes two changes has two. */
interface Step {
  title: string;
  /** How the note refers to the figure that changed: "the old figure" after a replacement, "this figure" otherwise. */
  subject: string;
  recalculation: Recalculation;
}

/** What was read from the document for a held figure, and where its printed label says it belongs. */
interface Reading {
  cell: HeldCell;
  /** The line the row's printed label names, when the figure can be filed under it from here. */
  target: LineDescription | null;
  /** What is on file for that line and period, held or in use. */
  targetFact?: FactSummary;
  targetOnFile: boolean;
  /** Both figures of a swapped pair are still held: the pair's own action covers this one. */
  inPair: boolean;
}

const quoted = (label: string | null) => (label ? `“${label}”` : 'its printed label');
const onPage = (page: number | null) => (page ? ` on page ${page}` : '');

/* ── One line's repair: one clear action, then the other choices ──────── */

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
  /** The statement's totals are on file for the period, so a changed figure is recalculated at once. */
  totalsOnFile: boolean;
  /** For a held figure: what was read. Absent for a line listed by a failed check. */
  reading?: Reading;
  /** Say what is on file above the controls, for a line shown without its own "On file" row. */
  withStatus?: boolean;
}

function Repair({ borrowerId, line, held, heldId, current, context, canAct, totalsOnFile, reading, withStatus }: RepairProps) {
  const confirm = useConfirmFact();
  const correct = useCorrectFact();
  const enter = useEnterFact();
  const reject = useRejectFact();
  const [mode, setMode] = useState<'different' | 'enter' | 'reject' | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [kept, setKept] = useState(false);
  const [filed, setFiled] = useState(false);
  /** The one-click action in flight: the row keeps saying what it is doing while the screen reads the figures again. */
  const [running, setRunning] = useState<Primary>(null);
  const willDoId = useId();

  const heldLive = held && (held.status === 'proposed' || held.status === 'verified' || held.status === 'confirmed') ? held : undefined;
  const heldOpen = heldLive?.status === 'proposed';
  /** The figure "Enter a different figure" replaces. */
  const replaceable = heldLive ?? (current && current.kind !== 'calculated' ? current : undefined);
  const name = `${line.label}${line.qualifier ? `, ${line.qualifier}` : ''}`;
  const cell = reading?.cell;
  const target = context ? (reading?.target ?? null) : null;

  // The held fact is still being read: nothing is offered until its state is known.
  const loading = Boolean(heldId) && !held;
  const cannotEnter =
    !replaceable && !current && !loading
      ? line.qualifier === 'printed total'
        ? 'A printed total cannot be entered: totals are calculated by code from their lines. Enter or replace the lines, or request a new document.'
        : line.qualifier === 'comparative column'
          ? 'A comparative-column figure cannot be entered from here.'
          : !line.input
            ? 'This line is a total calculated by code; it cannot be entered.'
            : !context
              ? 'The period of this spread is not recorded on the item, so a figure cannot be entered from here.'
              : null
      : null;

  const offered = canAct && !loading ? primaryAction({ heldOpen, onFile: Boolean(replaceable ?? current), target, targetOnFile: reading?.targetOnFile ?? false, inPair: reading?.inPair ?? false, canEnter: !cannotEnter }) : null;
  const primary = running ?? offered;
  const busy = running !== null || confirm.isPending;

  // Reasons for the one-click actions: what the person can see on the page, in words, never a figure.
  const fileReason = target ? `The row is printed ${quoted(cell?.row_label ?? null)}${onPage(cell?.page ?? null)}, so the figure is filed under ${target.label}, not ${line.label}.` : '';
  const rejectReason = target ? `The row is printed ${quoted(cell?.row_label ?? null)}${onPage(cell?.page ?? null)}, which names ${target.label}; ${target.label} already has a figure on file.` : '';

  const done = (step: Step) => {
    setSteps((before) => [...before, step]);
    setMode(null);
  };

  /** File under the line the label names: the figure is stored there, then this reading is set aside. Two ordinary calls. */
  async function file() {
    if (!target || !cell?.reads_as || !heldLive || !context) return;
    setRunning('file');
    setSteps([]);
    enter.reset();
    reject.reset();
    try {
      const stored = await enter.mutateAsync({ borrowerId, key: target.base, period_end: context.period_end, months: context.months, value: cell.reads_as.value, reason: fileReason });
      setFiled(true);
      setSteps([{ title: `What code recalculated when the figure was stored under ${target.label}`, subject: 'this figure', recalculation: stored.recalculation }]);
      const aside = await reject.mutateAsync({ factId: heldLive.id, reason: fileReason });
      setSteps((before) => [...before, { title: `What code recalculated when the reading under ${line.label} was set aside`, subject: 'this figure', recalculation: aside.recalculation }]);
    } catch {
      // The refusal is shown beside the button, in the server's own words.
    } finally {
      setRunning(null);
    }
  }

  async function setAside() {
    if (!heldLive) return;
    setRunning('reject');
    reject.reset();
    try {
      const aside = await reject.mutateAsync({ factId: heldLive.id, reason: rejectReason });
      done({ title: `What code recalculated when the reading under ${line.label} was set aside`, subject: 'this figure', recalculation: aside.recalculation });
    } catch {
      // The refusal is shown beside the button, in the server's own words.
    } finally {
      setRunning(null);
    }
  }

  const keep = () => heldLive && confirm.mutate(heldLive.id, { onSuccess: () => setKept(true) });

  const then = whatCodeWillDo(totalsOnFile);
  let willDo: ReactNode = null;
  let reason: string | null = null;
  if (primary === 'file' && target) {
    willDo = `Stores this figure under ${target.label} and sets the reading under ${line.label} aside, which leaves ${line.label} with nothing on file until its own figure is entered. ${then}`;
    reason = fileReason;
  } else if (primary === 'reject' && target) {
    willDo = (
      <>
        {target.label} already has {reading?.targetFact ? <FactFigure fact={reading.targetFact} weight="medium" /> : 'a figure'} on file, so this sets the reading aside and leaves {line.label} with nothing on file until its own figure is
        entered. {then}
      </>
    );
    reason = rejectReason;
  } else if (primary === 'keep') {
    const label = cell?.reason === 'mapping_doubt' && cell.row_label ? `, and accepts ${quoted(cell.row_label)} as a name for that line for this borrower from now on` : '';
    willDo = `Keeps this figure under ${line.label}, confirmed in your name${label}. No value changes, so nothing is recalculated${totalsOnFile ? '' : ' now: totals will be footed once the decision below is recorded'}.`;
  } else if (primary === 'enter') {
    willDo = `You enter the figure and a reason. ${then}`;
  }

  let status: ReactNode = null;
  if (withStatus) {
    if (heldLive?.status === 'confirmed') status = <StatusDot tone="pass">Confirmed by a person, as read</StatusDot>;
    else if (current) {
      status = (
        <span className="inline-flex flex-wrap items-baseline gap-x-1.5">
          <StatusDot tone={current.kind === 'manual' ? 'pass' : 'neutral'}>{current.kind === 'manual' ? 'Entered by a person. On file now:' : 'On file now:'}</StatusDot>
          <FactFigure fact={current} weight="medium" />
        </span>
      );
    }
  }

  const quiet = !reading;
  return (
    <div className="space-y-2">
      {status ? (
        <p className="text-body" data-repair-status>
          {status}
        </p>
      ) : null}
      {/* What the last click did, from the API's own summary, before what is offered next. */}
      {kept ? (
        <p role="status" className="text-body text-pretty text-ink-700" data-kept>
          Kept as read and confirmed in your name. No value changed, so code recalculated nothing.
        </p>
      ) : null}
      {filed && target ? (
        <p className="flex flex-wrap items-baseline gap-x-1.5 text-body" data-filed>
          <StatusDot tone="pass">Stored under {target.label}. On file there now:</StatusDot>
          {reading?.targetFact ? <FactFigure fact={reading.targetFact} weight="medium" /> : null}
        </p>
      ) : null}
      {steps.map((step, index) => (
        <RecalculationNote key={`${index}-${step.title}`} title={step.title} subject={step.subject} recalculation={step.recalculation} borrowerId={borrowerId} />
      ))}
      {canAct && mode === null && !loading && (primary || replaceable || heldOpen) ? (
        <div className="flex flex-wrap items-center gap-1.5" data-actions>
          {primary === 'file' && target ? (
            <Button variant="primary" size="sm" data-primary="file" aria-describedby={willDoId} disabled={busy} onClick={() => void file()}>
              {running === 'file' ? 'Filing' : `File under ${target.label}`}
            </Button>
          ) : null}
          {primary === 'reject' ? (
            <Button variant="primary" size="sm" data-primary="reject" aria-label={`Reject this reading of ${name}`} aria-describedby={willDoId} disabled={busy} onClick={() => void setAside()}>
              {running === 'reject' ? 'Rejecting' : 'Reject this reading'}
            </Button>
          ) : null}
          {primary === 'keep' ? (
            <Button variant="primary" size="sm" data-primary="keep" aria-label={`Keep as read: ${name}`} aria-describedby={willDoId} disabled={busy} onClick={keep}>
              {confirm.isPending ? 'Keeping' : 'Keep as read'}
            </Button>
          ) : null}
          {primary === 'enter' ? (
            <Button variant={quiet ? 'secondary' : 'primary'} size="sm" data-primary="enter" aria-label={`Enter the figure for ${name}`} aria-describedby={willDoId} onClick={() => (enter.reset(), setMode('enter'))}>
              Enter the figure
            </Button>
          ) : null}
          {heldOpen && primary !== 'keep' ? (
            <Button variant="ghost" size="sm" aria-label={`Keep as read: ${name}`} disabled={busy} onClick={keep}>
              {confirm.isPending ? 'Keeping' : 'Keep as read'}
            </Button>
          ) : null}
          {replaceable ? (
            <Button variant={quiet ? 'secondary' : 'ghost'} size="sm" aria-label={`Enter a different figure for ${name}`} disabled={busy} onClick={() => (correct.reset(), setMode('different'))}>
              Enter a different figure
            </Button>
          ) : null}
          {heldOpen && primary !== 'reject' ? (
            <Button variant="ghost" size="sm" aria-label={`Reject this reading of ${name}`} disabled={busy} onClick={() => (reject.reset(), setMode('reject'))}>
              Reject this reading
            </Button>
          ) : null}
        </div>
      ) : null}
      {canAct && mode === null && willDo ? (
        <p id={willDoId} className="text-body text-pretty text-ink-700" data-will-do>
          {willDo}
        </p>
      ) : null}
      {canAct && mode === null && reason && willDo ? <p className="text-caption text-pretty text-ink-500">Recorded in the ledger with your name, with this reason: “{reason}”</p> : null}
      {canAct && reading?.inPair ? <p className="text-caption text-pretty text-ink-500">The one action above covers this reading and the one it was swapped with. The choices here are the alternatives.</p> : null}
      {canAct && cannotEnter ? <p className="text-caption text-pretty text-ink-500">{cannotEnter}</p> : null}
      {confirm.error ? <Refusal error={confirm.error} outcome="Not kept" /> : null}
      {mode === null && enter.error ? <Refusal error={enter.error} outcome="Not filed" /> : null}
      {mode === null && reject.error ? <Refusal error={reject.error} outcome={filed ? `Stored under ${target?.label ?? 'the other line'}, but this reading was not set aside` : 'Not rejected'} /> : null}
      {mode === 'different' && replaceable ? (
        <FigureForm
          title={`Enter a different figure for ${name}`}
          unit={replaceable.unit}
          initialValue={replaceable.value}
          scale={context?.scale}
          submitLabel="Record the figure"
          pendingLabel="Recording"
          pending={correct.isPending}
          error={correct.error}
          reasonHint="Recorded in the ledger with your name. The figure on file now is kept in the history and marked superseded."
          onCancel={() => (correct.reset(), setMode(null))}
          onSubmit={({ value, reason: why }) => correct.mutate({ factId: replaceable.id, value, reason: why }, { onSuccess: (change) => done({ title: 'What code recalculated', subject: 'the old figure', recalculation: change.recalculation }) })}
        />
      ) : null}
      {mode === 'enter' && context ? (
        <FigureForm
          title={`Enter ${name}, ${periodPhrase(line, context)}`}
          unit="usd"
          scale={context.scale}
          submitLabel="Record the figure"
          pendingLabel="Recording"
          pending={enter.isPending}
          error={enter.error}
          reasonHint="Recorded in the ledger with your name, as a figure entered by a person."
          onCancel={() => (enter.reset(), setMode(null))}
          onSubmit={({ value, reason: why }) =>
            enter.mutate(
              { borrowerId, key: line.base, period_end: context.period_end, months: context.months, value, reason: why },
              { onSuccess: (change) => done({ title: 'What code recalculated', subject: 'this figure', recalculation: change.recalculation }) },
            )
          }
        />
      ) : null}
      {mode === 'reject' && heldLive ? (
        <FigureForm
          title={`Reject this reading of ${name}`}
          withValue={false}
          submitLabel="Record the rejection"
          pendingLabel="Recording"
          pending={reject.isPending}
          error={reject.error}
          reasonHint={`Recorded in the ledger with your name. ${line.label} then has no figure until one is entered.`}
          onCancel={() => (reject.reset(), setMode(null))}
          onSubmit={({ reason: why }) =>
            reject.mutate({ factId: heldLive.id, reason: why }, { onSuccess: (change) => done({ title: `What code recalculated when the reading under ${line.label} was set aside`, subject: 'this figure', recalculation: change.recalculation }) })
          }
        />
      ) : null}
    </div>
  );
}

/* ── The figure as printed, opening the page it is on ─────────────────── */

function usePageSource(cell: HeldCell, documentId: string | null, documentTitle: string, code?: string): (() => void) | null {
  const source = useSource();
  const page = cell.page;
  if (cell.fact_id) return () => source.open({ type: 'fact', id: cell.fact_id as string });
  if (!documentId || !page) return null;
  return () => source.open({ type: 'document', documentId, page, quote: cell.printed_figure ?? undefined, title: documentTitle, borrowerCode: code });
}

function PrintedFigure({ cell, line, open }: { cell: HeldCell; line: LineDescription; open: (() => void) | null }) {
  if (!cell.printed_figure) return <span className="text-ink-500">No figure read</span>;
  const figure = (
    <>
      <span className="tnum whitespace-nowrap">{cell.printed_figure}</span>
      <ProvenanceGlyph kind="extracted" />
    </>
  );
  if (!open) return <span className="inline-flex items-center gap-1 font-medium text-ink">{figure}</span>;
  return (
    <button
      type="button"
      data-printed-figure
      aria-label={`${cell.printed_figure}, ${line.label} as printed${onPage(cell.page)}. Read from a document. Show source.`}
      onClick={open}
      className="-mx-1 inline-flex items-center gap-1 rounded-xs px-1 font-medium text-ink t-colors hover:bg-cobalt-bg hover:text-cobalt-strong"
    >
      {figure}
    </button>
  );
}

/* ── One held figure: on file, read from the document, why it was held ── */

const termClass = 'eyebrow pt-[3px]';
const blockClass = 'grid grid-cols-1 gap-x-4 gap-y-0.5 @xl:grid-cols-[13.5rem_minmax(0,1fr)] @xl:gap-y-2';

interface HeldRowProps {
  borrowerId: string;
  cell: HeldCell;
  line: LineDescription;
  held?: FactSummary;
  current?: FactSummary;
  /** The held facts are still being read. */
  loading: boolean;
  context: SpreadContext | null;
  canAct: boolean;
  totalsOnFile: boolean;
  reading: Reading;
  documentId: string | null;
  documentTitle: string;
  code?: string;
}

function HeldRow({ borrowerId, cell, line, held, current, loading, context, canAct, totalsOnFile, reading, documentId, documentTitle, code }: HeldRowProps) {
  const open = usePageSource(cell, documentId, documentTitle, code);
  const heldLive = held && (held.status === 'proposed' || held.status === 'verified' || held.status === 'confirmed') ? held : undefined;
  const waiting = needsPerson(cell.fact_id, held, current);
  const why = whyHeld(cell, line, reading.target);

  // What is stored for the line and period now: the held figure itself until a person decides, then whatever replaced it.
  let onFile: ReactNode;
  if (current) {
    onFile = (
      <>
        <FactFigure fact={current} weight="medium" />
        <span className="text-ink-700">{current.kind === 'manual' ? 'entered by a person' : 'in use'}</span>
      </>
    );
  } else if (heldLive) {
    onFile = (
      <>
        <FactFigure fact={heldLive} weight="medium" />
        <span className="text-ink-700">{heldLive.status === 'proposed' ? 'held: not used in any calculation until a person decides' : 'confirmed by a person, as read'}</span>
      </>
    );
  } else if (cell.fact_id && !held && loading) {
    onFile = <span className="text-ink-500">Reading what is on file</span>;
  } else {
    onFile = (
      <>
        <span className="font-medium text-ink">Nothing on file</span>
        {held?.status === 'rejected' ? <span className="text-ink-700">the reading was rejected</span> : null}
      </>
    );
  }

  const cleared = heldLive?.status === 'confirmed' ? 'Cleared: kept as read' : current?.kind === 'manual' ? 'Cleared: a person entered the figure on file' : 'Cleared';
  const thousands = context?.scale === 1000;

  return (
    <li data-held-row={cell.key} aria-label={`Held figure: ${line.label}${line.qualifier ? `, ${line.qualifier}` : ''}`} className="border-b border-hairline py-3 last:border-b-0">
      <dl className={blockClass}>
        <dt className={termClass}>On file</dt>
        <dd data-on-file className="min-w-0 text-body">
          <span className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-medium text-ink">{line.label}</span>
            {onFile}
          </span>
          <span className="block text-caption text-ink-500">
            {line.statement}
            {line.qualifier ? `, ${line.qualifier}` : ''}
            {context && !line.qualifier ? `, ${periodPhrase(line, context)}` : ''}
          </span>
        </dd>

        <dt className={`${termClass} mt-2 @xl:mt-0`}>Read from the document</dt>
        <dd data-read className="min-w-0 text-body">
          <span className="flex flex-wrap items-baseline gap-x-2">
            {cell.row_label ? <span className="font-medium text-ink">“{cell.row_label}”</span> : <span className="text-ink-700">No row label could be read</span>}
            <PrintedFigure cell={cell} line={line} open={open} />
            {cell.printed_figure ? <span className="text-ink-700">as printed{thousands ? ', in thousands' : ''}</span> : null}
          </span>
          <span className="block text-caption text-ink-500">
            {!cell.row_label && cell.printed_label ? <>The reader reported “{cell.printed_label}”. </> : null}
            {cell.page && open ? (
              <button type="button" data-open-page onClick={open} className="rounded-xs font-medium text-cobalt underline-offset-2 t-colors hover:text-cobalt-strong hover:underline">
                Open page {cell.page}
              </button>
            ) : cell.page ? (
              `Page ${cell.page}`
            ) : null}
            {cell.page ? `, ${documentTitle}` : null}
            {held?.status === 'rejected' ? '. This reading was rejected.' : held?.status === 'superseded' ? '. This reading was replaced by the figure on file.' : null}
          </span>
        </dd>

        <dt className={`${termClass} mt-2 @xl:mt-0`}>Why it was held</dt>
        <dd data-why className="min-w-0 text-body text-pretty text-ink">
          {why.sentence}
          {why.detail ? <span className="block text-caption text-ink-500">The check reported: {why.detail}</span> : null}
        </dd>

        <dt className="sr-only">What to do</dt>
        <dd className="mt-2 min-w-0 space-y-2 @xl:col-start-2 @xl:mt-0">
          <p className="text-body" data-row-status>
            <StatusDot tone={waiting ? 'attention' : 'muted'}>{waiting ? 'Needs a person' : cleared}</StatusDot>
          </p>
          <Repair borrowerId={borrowerId} line={line} held={held} heldId={cell.fact_id} current={current} context={context} canAct={canAct} totalsOnFile={totalsOnFile} reading={reading} />
        </dd>
      </dl>
    </li>
  );
}

/* ── Two readings that look swapped: one action for both ──────────────── */

interface Side {
  cell: HeldCell;
  line: LineDescription;
}

function SwappedPair({ first, second, live, canAct, totalsOnFile, borrowerId }: { first: Side; second: Side; live: boolean; canAct: boolean; totalsOnFile: boolean; borrowerId: string }) {
  const correctFirst = useCorrectFact();
  const correctSecond = useCorrectFact();
  const [steps, setSteps] = useState<Step[]>([]);
  const [busy, setBusy] = useState(false);
  const willDoId = useId();
  const refused = correctFirst.error ?? correctSecond.error;
  // Once neither figure is held any more there is nothing to offer; what this session did stays on show.
  if (!live && !busy && steps.length === 0 && !refused) return null;

  /** What code found, in words; it is also the reason recorded with each correction. It names rows and lines, never a figure. */
  const finding = `The row printed ${quoted(first.cell.row_label)} was filed under ${first.line.label}, and the row printed ${quoted(second.cell.row_label)} under ${second.line.label}.`;
  const reason = `Two readings${onPage(first.cell.page)} were filed under each other’s lines. ${finding} Each figure is now filed under the line its printed label names.`;

  async function fileBoth() {
    if (!first.cell.fact_id || !second.cell.fact_id || !first.cell.reads_as || !second.cell.reads_as) return;
    setBusy(true);
    try {
      const one = await correctFirst.mutateAsync({ factId: first.cell.fact_id, value: second.cell.reads_as.value, reason });
      setSteps([{ title: `What code recalculated when ${first.line.label} was corrected`, subject: 'the old figure', recalculation: one.recalculation }]);
      const two = await correctSecond.mutateAsync({ factId: second.cell.fact_id, value: first.cell.reads_as.value, reason });
      setSteps((before) => [...before, { title: `What code recalculated when ${second.line.label} was corrected`, subject: 'the old figure', recalculation: two.recalculation }]);
    } catch {
      // The refusal is shown beside the button, in the server's own words.
    } finally {
      setBusy(false);
    }
  }

  const offer = (live || busy) && canAct && steps.length < 2 && !refused;
  return (
    <div data-swapped-pair className="space-y-2 rounded-md border border-hairline-strong bg-canvas px-3 py-2.5">
      <p className="text-body text-pretty text-ink">
        <span className="font-medium">Two readings look swapped.</span> {finding}
      </p>
      {offer ? (
        <>
          <Button variant="primary" size="sm" data-primary="swap" aria-describedby={willDoId} disabled={busy} onClick={() => void fileBoth()}>
            {busy ? 'Filing both' : 'File both under the lines their labels name'}
          </Button>
          <p id={willDoId} className="text-body text-pretty text-ink-700" data-will-do>
            Stores each figure under the line its printed label names, as two corrections in your name. {whatCodeWillDo(totalsOnFile)}
          </p>
          <p className="text-caption text-pretty text-ink-500">Both corrections are recorded in the ledger with your name, with the finding above as the reason.</p>
        </>
      ) : null}
      {steps.length === 2 ? (
        <p className="text-body" role="status" data-swap-result>
          <StatusDot tone="pass">Both filed under the lines their labels name</StatusDot>
        </p>
      ) : null}
      {refused ? (
        <Refusal error={refused} outcome={steps.length === 1 ? `${first.line.label} was corrected, but ${second.line.label} was not` : 'Not filed'} />
      ) : null}
      {steps.map((step) => (
        <RecalculationNote key={step.title} title={step.title} subject={step.subject} recalculation={step.recalculation} borrowerId={borrowerId} />
      ))}
    </div>
  );
}

/* ── Enter or replace any line of the statement ───────────────────────── */

function AnyLine({ borrowerId, lines, context, currentOf, suggested, totalsOnFile }: { borrowerId: string; lines: SpreadLineApi[]; context: SpreadContext; currentOf: (base: string) => FactSummary | undefined; suggested: string[]; totalsOnFile: boolean }) {
  const inputs = lines.filter((line) => !line.computed);
  const [open, setOpen] = useState(false);
  const [picked, setKey] = useState('');
  if (inputs.length === 0) return null;
  if (!open) {
    return (
      <Button size="sm" onClick={() => setOpen(true)}>
        Enter a figure for another line
      </Button>
    );
  }
  // The lines arrive after the item does: until the person picks one, start from the first line a check named.
  const has = (candidate: string) => inputs.some((entry) => entry.key === candidate);
  const key = has(picked) ? picked : (suggested.find(has) ?? inputs[0]?.key ?? '');
  const line = describeLine(key, lines);
  return (
    <div className="space-y-2 rounded-md border border-hairline bg-canvas px-3 py-2.5" data-any-line>
      <Select
        label={`Line of the statement, period ended ${formatDate(context.period_end)}`}
        value={key}
        onValueChange={setKey}
        options={inputs.map((entry) => ({ value: entry.key, label: `${STATEMENT_LABEL[entry.statement] ?? humanize(entry.statement)} · ${entry.label}` }))}
      />
      {currentOf(key) ? null : <p className="text-caption text-ink-500">Nothing is on file for this line and period.</p>}
      <Repair key={key} borrowerId={borrowerId} line={line} heldId={null} current={currentOf(key)} context={context} canAct totalsOnFile={totalsOnFile} withStatus />
    </div>
  );
}

/* ── The section on the work item ─────────────────────────────────────── */

const cellClass = 'py-1.5 align-top';
const headClass = 'eyebrow border-b border-ink py-1 text-left font-semibold';

/**
 * Repair of a held spread, on the work item itself. Each held figure says three things in order:
 * what is on file for the line it was filed under, what was read from the document (the label and
 * the figure as printed, with the page), and why code held it. One action is offered first and
 * its label says what it does; the other choices sit beside it. Two readings filed under each
 * other's lines are named as a pair, with one action for both. What the click did is then shown
 * from the API's own summary. The decision that finishes the spread stays below, with the person.
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
  const pairs = useMemo(() => swappedPairs(cells, lines), [cells, lines]);

  /** What the spread holds for a line and the period: a figure in use, or one held for a person. */
  const cellOf = (base: string) => (context ? lines.find((line) => line.key === base)?.cells[context.period_end] : undefined);
  const onFile = (base: string) => {
    const cell = cellOf(base);
    return cell?.usable ? cell.fact_id : null;
  };
  const targetOf = (cell: HeldCell) => (cell.reads_as ? describeLine(cell.reads_as.key, lines) : null);
  const rowKeys = [...cells.map((cell) => describeLine(cell.key, lines).base), ...problems.flatMap((problem) => (problem.key ? [describeLine(problem.key, lines).base] : []))];
  const facts = useFactsById([
    ...cells.map((cell) => cell.fact_id),
    ...rowKeys.map(onFile),
    ...cells.map((cell) => cellOf(targetOf(cell)?.base ?? '')?.fact_id),
    ...lines.filter((line) => !line.computed).map((line) => (doesNotFoot ? onFile(line.key) : null)),
  ]);
  const fact = (id: string | null | undefined) => (id ? facts.data?.[id] : undefined);
  const currentOf = (base: string, heldId: string | null = null) => {
    const id = onFile(base);
    return id && id !== heldId ? fact(id) : undefined;
  };

  if (!relevant) return null;

  const documentId = context?.document_id ?? str(item.evidence.document_id);
  const documentTitle = documents.data?.find((row) => row.id === documentId)?.title ?? 'Statement on file';
  const permitted = can(item.required_permission);
  const canAct = permitted && item.status === 'open';
  const totalsOnFile = Boolean(context && lines.some((line) => line.computed && line.cells[context.period_end]?.usable));
  const waiting = cells.filter((cell) => needsPerson(cell.fact_id, fact(cell.fact_id), currentOf(describeLine(cell.key, lines).base, cell.fact_id))).length;
  const holders = (ROLES_WITH[item.required_permission] ?? []).map(roleLabel);
  const stillHeld = (index: number) => fact(cells[index]?.fact_id)?.status === 'proposed';
  const livePairs = pairs.filter(([i, j]) => stillHeld(i) && stillHeld(j));
  const side = (index: number): Side => ({ cell: cells[index] as HeldCell, line: describeLine((cells[index] as HeldCell).key, lines) });

  return (
    <section aria-label="Held figures and their repair" data-held-figures className="@container space-y-3">
      {cells.length > 0 ? (
        <div>
          <div className="flex flex-wrap items-baseline gap-x-2 border-b border-ink pb-1">
            <Heading className="eyebrow">Held figures</Heading>
            <span className="text-caption text-ink-500" aria-live="polite" data-held-count>
              {facts.isPending && cells.some((cell) => cell.fact_id) ? `${cells.length} held` : waiting === 0 ? `All ${cells.length} cleared; record the decision below` : `${waiting} of ${cells.length} still ${waiting === 1 ? 'needs' : 'need'} a person`}
            </span>
          </div>
          {pairs.map(([i, j]) => (
            <div key={`${i}-${j}`} className="pt-3 empty:hidden">
              <SwappedPair first={side(i)} second={side(j)} live={stillHeld(i) && stillHeld(j)} canAct={canAct} totalsOnFile={totalsOnFile} borrowerId={item.borrower_id} />
            </div>
          ))}
          <ul aria-label="Held figures">
            {cells.map((cell, index) => {
              const line = describeLine(cell.key, lines);
              const named = targetOf(cell);
              // The figure can be filed under the line its label names only when both are input lines for the period itself.
              const target = named && named.input && line.input ? named : null;
              const targetCell = target ? cellOf(target.base) : undefined;
              return (
                <HeldRow
                  key={`${cell.key}-${index}`}
                  borrowerId={item.borrower_id}
                  cell={cell}
                  line={line}
                  held={fact(cell.fact_id)}
                  current={currentOf(line.base, cell.fact_id)}
                  loading={facts.isPending}
                  context={context}
                  canAct={canAct}
                  totalsOnFile={totalsOnFile}
                  reading={{ cell, target, targetFact: fact(targetCell?.fact_id), targetOnFile: Boolean(targetCell), inPair: livePairs.some((pair) => pair.includes(index)) }}
                  documentId={documentId}
                  documentTitle={documentTitle}
                  code={code}
                />
              );
            })}
          </ul>
        </div>
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
                    ) : problem.message && !knownCheck(problem.code) ? (
                      <p className="text-caption text-pretty text-ink-500">{problem.message}</p>
                    ) : null}
                    {line?.input && problem.code === 'missing_input' ? (
                      <div className="mt-1.5">
                        <Repair borrowerId={item.borrower_id} line={line} heldId={null} current={currentOf(line.base)} context={context} canAct={canAct} totalsOnFile={totalsOnFile} withStatus />
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
        <p className="text-body text-pretty text-ink-700">This item does not list the figures or checks behind it. A figure can still be entered for any line of the period below.</p>
      ) : null}
      {doesNotFoot && canAct && context ? (
        <AnyLine borrowerId={item.borrower_id} lines={lines} context={context} currentOf={(base) => currentOf(base)} suggested={problems.flatMap((problem) => (problem.key ? [problem.key] : []))} totalsOnFile={totalsOnFile} />
      ) : null}
      {!permitted && item.status === 'open' && user ? (
        <p className="text-caption text-pretty text-ink-700">
          Keeping, entering and rejecting figures needs {holders.length > 0 ? `a ${holders.join(' or a ').toLowerCase()}` : 'another role'}. Your role, {roleLabel(user.role)}, can read the held figures and open their pages.
        </p>
      ) : null}
    </section>
  );
}
