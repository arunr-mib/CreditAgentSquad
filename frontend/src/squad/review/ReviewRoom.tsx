import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo, useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import {
  useActions,
  useBorrowers,
  useCreateAction,
  useCreateMeeting,
  useCycles,
  useFactsById,
  useMeetings,
  useReviewSheet,
  useReviewSheets,
  useSetActionStatus,
  useSetMeetingPhase,
  useUsers,
  useWorkItems,
} from '@/api/hooks';
import type { ActionRow, Meeting, ReviewSheetDetail } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { Button, Card, CardHeader, formatDate, Input, PageHeader, Select, StatusDot, Stepper, type Step } from '@/design';
import { humanize, OUTCOME, quarterLabel } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { FactFigure } from '@/source/figures';
import { EmptyCard, ErrorNotice, Load, Notice, SeverityDot } from '@/screens/parts';
import { Commentary } from '@/squad/clientfile/review/Commentary';
import { CasePanel } from '../case/CasePanel';
import { useSignalWords } from '../DocType';
import { clientFile, threadHref } from '../links';
import { usePresence } from '../presence/Presence';

const PHASES: Array<{ id: Meeting['phase']; label: string; detail: string }> = [
  { id: 'before', label: 'Before', detail: 'Sheets are prepared and commentary is approved' },
  { id: 'during', label: 'During', detail: 'Decisions and actions are recorded' },
  { id: 'after', label: 'After', detail: 'Actions are followed to completion' },
  { id: 'closed', label: 'Closed', detail: 'The record is final' },
];

function MeetingCard({ meeting, onOpenSheet, sheetId }: { meeting: Meeting; onOpenSheet: (id: string) => void; sheetId: string | undefined }) {
  const setPhase = useSetMeetingPhase();
  const { can } = useAuth();
  const { say } = usePresence();
  const index = PHASES.findIndex((phase) => phase.id === meeting.phase);
  const next = PHASES[index + 1];
  const steps: Step[] = PHASES.map((phase, position) => ({
    id: phase.id,
    label: phase.label,
    status: position < index ? 'done' : position === index ? (phase.id === 'closed' ? 'done' : 'running') : 'pending',
    detail: phase.detail,
  }));
  return (
    <Card data-meeting={meeting.id}>
      <CardHeader
        as="h2"
        eyebrow={`Review meeting · ${quarterLabel(meeting.period_end)}`}
        title={meeting.title}
        meta={`${formatDate(meeting.meeting_date)} · ${meeting.sheets.length} review ${meeting.sheets.length === 1 ? 'sheet' : 'sheets'}`}
        actions={
          next && can('manage_actions') ? (
            <Button
              variant="primary"
              disabled={setPhase.isPending}
              onClick={() => setPhase.mutate({ id: meeting.id, phase: next.id }, { onSuccess: () => say(`Meeting moved to: ${next.label.toLowerCase()} · recorded`) })}
            >
              Move to {next.label.toLowerCase()}
            </Button>
          ) : undefined
        }
      />
      <div className="border-t border-hairline px-4 pt-3 pb-3.5">
        <Stepper label="Phases of the review meeting" steps={steps} />
        {setPhase.error ? (
          <Notice tone="attention" title="The phase was not changed" className="mt-3">
            The server said: “{errorMessage(setPhase.error)}”
          </Notice>
        ) : null}
      </div>
      <div className="border-t border-hairline-strong">
        <h3 className="eyebrow px-4 pt-3 pb-1.5">Review sheets on the agenda</h3>
        {meeting.sheets.length === 0 ? (
          <p className="border-t border-hairline px-4 py-3 text-body text-pretty text-ink-700">
            No review sheet is attached. Sheets for the period are attached when the meeting is created; none had been prepared for {quarterLabel(meeting.period_end)}. A sheet is prepared
            when a cycle reaches review preparation and the Review Agent has drafted its commentary.
          </p>
        ) : (
          <ul className="border-t border-ink">
            {meeting.sheets.map((sheet) => (
              <li key={sheet.id} className="border-b border-hairline last:border-b-0">
                <button type="button" aria-pressed={sheet.id === sheetId} onClick={() => onOpenSheet(sheet.id)} className="flex min-h-[34px] w-full items-center justify-between gap-4 px-4 py-1.5 text-left text-body t-colors hover:bg-hover aria-pressed:bg-cobalt-bg last:rounded-b-md">
                  <span className="font-medium text-ink">{sheet.borrower_name}</span>
                  <StatusDot tone={sheet.status === 'reviewed' || sheet.status === 'released' ? 'pass' : 'attention'}>{sheet.status === 'draft' ? 'Draft, not yet approved' : humanize(sheet.status)}</StatusDot>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

function NewMeeting({ periods }: { periods: string[] }) {
  const create = useCreateMeeting();
  const { say } = usePresence();
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [period, setPeriod] = useState(periods[0] ?? '');
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !date || !period) return;
    create.mutate(
      { title: title.trim(), meeting_date: date, period_end: period },
      {
        onSuccess: () => {
          say('Meeting created · review sheets for the period attached · recorded');
          setTitle('');
          setDate('');
        },
      },
    );
  }
  return (
    <Card>
      <CardHeader as="h2" title="New review meeting" meta="Every review sheet for the period that has no meeting yet is attached" />
      <form onSubmit={submit} className="space-y-3 border-t border-hairline px-4 pt-3 pb-4">
        <Input label="Title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Quarterly portfolio review" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Input label="Meeting date" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          <Select label="Period reviewed" value={period} onValueChange={setPeriod} options={periods.map((value) => ({ value, label: `${quarterLabel(value)} · ${formatDate(value)}` }))} />
        </div>
        {create.error ? (
          <Notice tone="attention" title="The meeting was not created">
            The server said: “{errorMessage(create.error)}”
          </Notice>
        ) : null}
        <Button type="submit" variant="primary" disabled={create.isPending || !title.trim() || !date || !period}>
          {create.isPending ? 'Creating' : 'Create the meeting'}
        </Button>
      </form>
    </Card>
  );
}

function Sheet({ sheet }: { sheet: ReviewSheetDetail }) {
  const navigate = useNavigate();
  const signalWords = useSignalWords();
  const ids = useMemo(() => {
    const out: Array<string | null> = [];
    for (const metric of sheet.content.metrics ?? []) out.push(metric.current, metric.year_earlier);
    for (const covenant of sheet.content.covenants ?? []) out.push(covenant.value, covenant.threshold, covenant.headroom_pct, covenant.reported);
    out.push(sheet.content.collateral?.availability ?? null);
    return out;
  }, [sheet]);
  const facts = useFactsById(ids);
  const items = useWorkItems({ status: 'open', borrower_id: sheet.borrower_id });
  const approval = items.data?.find((item) => item.item_type === 'review.commentary_approval' && item.review_sheet_id === sheet.id);
  const fact = (id: string | null | undefined) => (id ? facts.data?.[id] : undefined);
  const borrowers = useBorrowers();
  const code = borrowers.data?.find((row) => row.id === sheet.borrower_id)?.code;

  return (
    <div data-review-sheet={sheet.id} className={cx('grid items-start gap-5', approval && 'xl:grid-cols-[minmax(0,1fr)_400px]')}>
      <Card className="min-w-0">
        <CardHeader
          as="h2"
          className="max-sm:flex-wrap max-sm:gap-y-1"
          eyebrow={`Review sheet · ${quarterLabel(sheet.period_end)}`}
          title={sheet.borrower_name}
          meta={
            <>
              Assembled by code from stored facts · risk rating <span className="tnum">{sheet.content.risk_rating ?? 'not set'}</span>
              {code ? (
                <>
                  {' · '}
                  <Link to={clientFile(code)} className="link">
                    Open the client file
                  </Link>
                </>
              ) : null}
            </>
          }
          actions={
            sheet.status === 'draft' ? (
              <StatusDot tone="attention">Draft, not yet approved</StatusDot>
            ) : (
              <StatusDot tone="pass">
                {humanize(sheet.status)}
                {sheet.approved_by_name ? ` by ${sheet.approved_by_name}` : ''}
              </StatusDot>
            )
          }
        />
        <div className="border-t border-hairline px-4 pt-3.5 pb-4">
          <Commentary key={sheet.id} sheet={sheet} />
        </div>
        {(sheet.content.metrics ?? []).length > 0 ? (
          <table className="w-full border-separate border-spacing-0 text-body max-sm:[&_:is(th,td)]:px-2 max-sm:[&_:is(th,td):first-child]:pl-4 max-sm:[&_:is(th,td):last-child]:pr-4">
            <caption className="eyebrow border-t border-hairline-strong px-4 pt-3 pb-1.5 text-left">Performance</caption>
            <thead>
              <tr>
                <th scope="col" className="eyebrow h-8 border-b border-ink px-4 text-left">
                  Measure
                </th>
                <th scope="col" className="eyebrow h-8 w-28 border-b border-ink px-4 text-right sm:w-44">
                  This period
                </th>
                <th scope="col" className="eyebrow h-8 w-28 border-b border-ink px-4 text-right sm:w-44">
                  A year earlier
                </th>
              </tr>
            </thead>
            <tbody>
              {(sheet.content.metrics ?? []).map((metric) => (
                <tr key={metric.metric}>
                  <th scope="row" className="h-[34px] border-b border-hairline px-4 text-left font-regular text-ink-700">
                    {metric.label}
                  </th>
                  <td className="border-b border-hairline px-4 text-right">
                    <FactFigure fact={fact(metric.current)} scale={fact(metric.current)?.unit === 'usd' ? 1000 : 1} align="column" weight="medium" />
                  </td>
                  <td className="border-b border-hairline px-4 text-right">
                    <FactFigure fact={fact(metric.year_earlier)} scale={fact(metric.year_earlier)?.unit === 'usd' ? 1000 : 1} align="column" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {(sheet.content.covenants ?? []).length > 0 ? (
          <table className="stack-narrow w-full border-separate border-spacing-0 text-body">
            <caption className="eyebrow px-4 pt-4 pb-1.5 text-left">Covenants</caption>
            <thead>
              <tr>
                {['Covenant', 'Calculated', 'Required', 'Headroom', 'Certificate', 'Outcome'].map((head, index) => (
                  <th key={head} scope="col" className={cx('eyebrow h-8 border-b border-ink px-4', index > 0 && index < 5 ? 'text-right' : 'text-left')}>
                    {head}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(sheet.content.covenants ?? []).map((covenant) => (
                <tr key={covenant.covenant}>
                  <th scope="row" className="h-[34px] border-b border-hairline px-4 text-left font-medium text-ink">
                    {covenant.covenant}
                  </th>
                  {[covenant.value, covenant.threshold, covenant.headroom_pct, covenant.reported].map((id, index) => (
                    <td key={index} data-label={['Calculated', 'Required', 'Headroom', 'Certificate'][index]} className="border-b border-hairline px-4 text-right">
                      <FactFigure fact={fact(id)} weight={index === 0 ? 'semibold' : 'regular'} />
                    </td>
                  ))}
                  <td data-label="Outcome" className="border-b border-hairline px-4">
                    <StatusDot tone={OUTCOME[covenant.outcome].tone} emphasis={OUTCOME[covenant.outcome].emphasis} className="max-[1279px]:whitespace-normal!">
                      {OUTCOME[covenant.outcome].label}
                    </StatusDot>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {(sheet.content.signals ?? []).length > 0 ? (
          <div className="px-4 pt-4 pb-3">
            <h3 className="eyebrow mb-1">Signals</h3>
            <ul className="border-t border-ink">
              {(sheet.content.signals ?? []).map((signal) => (
                <li key={signal.signal_id} className="flex min-h-[34px] items-center gap-4 border-b border-hairline py-1.5 text-body last:border-b-0">
                  <SeverityDot severity={signal.severity} />
                  <span className="font-medium text-ink">{signalWords(signal.rule)}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Card>
      {approval ? (
        <aside aria-label="Approval of this commentary" data-work-item={approval.id} className="xl:sticky xl:top-[68px] xl:max-h-[calc(100vh-88px)] xl:overflow-y-auto xl:rounded-md">
          <h3 className="sq-h2">{approval.title}</h3>
          <p className="sq-muted">{approval.question}</p>
          <CasePanel key={approval.id} workItemId={approval.id} onOpenCase={(id) => code && void navigate(threadHref(code, id))} />
        </aside>
      ) : null}
    </div>
  );
}

function Actions({ meetingId }: { meetingId: string | undefined }) {
  const actions = useActions({ status: 'all' });
  const borrowers = useBorrowers();
  const users = useUsers();
  const create = useCreateAction();
  const setStatus = useSetActionStatus();
  const { can } = useAuth();
  const { say } = usePresence();
  const [borrowerId, setBorrowerId] = useState('none');
  const [title, setTitle] = useState('');
  const [owner, setOwner] = useState('none');
  const [due, setDue] = useState('');
  const [closing, setClosing] = useState<{ id: string; note: string } | null>(null);
  const allowed = can('manage_actions');

  function submit(event: FormEvent) {
    event.preventDefault();
    if (borrowerId === 'none' || !title.trim()) return;
    create.mutate(
      { borrower_id: borrowerId, title: title.trim(), owner_id: owner === 'none' ? null : owner, due_date: due || null, meeting_id: meetingId ?? null },
      {
        onSuccess: () => {
          say('Action raised · recorded');
          setTitle('');
          setDue('');
        },
      },
    );
  }

  const change = (action: ActionRow, status: ActionRow['status'], note?: string) =>
    setStatus.mutate({ id: action.id, status, note }, { onSuccess: () => (setClosing(null), say(`Action marked ${humanize(status).toLowerCase()} · recorded`)) });

  return (
    <Card>
      <CardHeader as="h2" title="Actions" meta="Each action has an owner and a due date. Closing one needs a note saying what was done." />
      <Load query={actions} what="The actions" rows={3}>
        {(rows) =>
          rows.length === 0 ? (
            <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">No action has been raised yet.</p>
          ) : (
            <ul className="border-t border-ink" data-actions>
              {rows.map((action) => {
                const open = action.status === 'open' || action.status === 'in_progress';
                return (
                  <li key={action.id} className="border-b border-hairline px-4 py-2 text-body last:border-b-0">
                    <div className="grid grid-cols-1 items-center gap-x-4 gap-y-1 md:grid-cols-[minmax(0,1fr)_170px_150px_auto]">
                      <div className="min-w-0">
                        <p className="font-medium text-pretty text-ink">{action.title}</p>
                        <p className="text-caption text-ink-500">{action.borrower_name}</p>
                      </div>
                      <span className="text-ink-700">{action.owner_name ?? 'No owner'}</span>
                      <StatusDot tone={action.overdue ? 'attention' : action.status === 'done' ? 'pass' : action.status === 'cancelled' ? 'muted' : 'neutral'} emphasis={action.overdue}>
                        {action.status === 'done' ? 'Done' : action.status === 'cancelled' ? 'Cancelled' : action.due_date ? `${action.overdue ? 'Overdue, ' : 'Due '}${formatDate(action.due_date)}` : humanize(action.status)}
                      </StatusDot>
                      <span className="flex gap-1.5 md:justify-end">
                        {open && allowed ? (
                          <>
                            {action.status === 'open' ? (
                              <Button size="sm" disabled={setStatus.isPending} onClick={() => change(action, 'in_progress')}>
                                Start
                              </Button>
                            ) : null}
                            <Button size="sm" onClick={() => setClosing({ id: action.id, note: '' })}>
                              Mark done
                            </Button>
                          </>
                        ) : null}
                      </span>
                    </div>
                    {action.closing_note ? <p className="mt-1 text-caption text-ink-700">Closing note: {action.closing_note}</p> : null}
                    {closing?.id === action.id ? (
                      <form
                        className="mt-2 flex flex-wrap items-end gap-2"
                        onSubmit={(event) => {
                          event.preventDefault();
                          change(action, 'done', closing.note);
                        }}
                      >
                        <Input label="What was done" className="flex-1" value={closing.note} onChange={(event) => setClosing({ id: action.id, note: event.target.value })} />
                        <Button type="submit" variant="primary" disabled={setStatus.isPending || !closing.note.trim()}>
                          Record as done
                        </Button>
                        <Button variant="ghost" onClick={() => setClosing(null)}>
                          Cancel
                        </Button>
                      </form>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )
        }
      </Load>
      {setStatus.error ? (
        <div className="border-t border-hairline px-4 py-3">
          <Notice tone="attention" title="The action was not changed">
            The server said: “{errorMessage(setStatus.error)}”
          </Notice>
        </div>
      ) : null}
      {allowed ? (
        <form onSubmit={submit} className="grid grid-cols-1 items-end gap-3 border-t sm:grid-cols-2 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1.6fr)_minmax(0,1fr)_150px_auto] border-hairline-strong px-4 pt-3 pb-4">
          <Select label="Client" value={borrowerId} onValueChange={setBorrowerId} options={[{ value: 'none', label: 'Choose a client' }, ...(borrowers.data ?? []).map((row) => ({ value: row.id, label: row.name }))]} />
          <Input label="Action" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What must be done" />
          <Select label="Owner" value={owner} onValueChange={setOwner} options={[{ value: 'none', label: 'No owner yet' }, ...(users.data ?? []).map((user) => ({ value: user.id, label: user.name }))]} />
          <Input label="Due" type="date" value={due} onChange={(event) => setDue(event.target.value)} />
          <Button type="submit" variant="primary" disabled={create.isPending || borrowerId === 'none' || !title.trim()}>
            Raise the action
          </Button>
          {create.error ? (
            <div className="col-span-full">
              <Notice tone="attention" title="The action was not raised">
                The server said: “{errorMessage(create.error)}”
              </Notice>
            </div>
          ) : null}
        </form>
      ) : (
        <p className="border-t border-hairline-strong px-4 py-3 text-caption text-ink-500">Your role can read actions but not raise or change them; the server decides who may.</p>
      )}
    </Card>
  );
}

export function ReviewRoom() {
  const meetings = useMeetings();
  const sheets = useReviewSheets();
  const cycles = useCycles();
  const search = useSearch({ from: '/review-room' });
  const navigate = useNavigate({ from: '/review-room' });
  const { can } = useAuth();
  const sheet = useReviewSheet(search.sheet);
  const periods = useMemo(() => [...new Set((cycles.data ?? []).map((cycle) => cycle.period_end))].sort().reverse().slice(0, 8), [cycles.data]);
  const selected = meetings.data?.find((meeting) => meeting.id === search.meeting) ?? meetings.data?.[0];
  const openSheet = (id: string) => void navigate({ search: (previous) => ({ ...previous, sheet: id }), replace: true, resetScroll: false });
  const loose = (sheets.data ?? []).filter((row) => !row.meeting_id);

  return (
    <div data-ready={meetings.data ? '' : undefined} className="space-y-5">
      <PageHeader eyebrow="Credit Squad" title="Review room" meta={<span>Before the meeting: sheets and commentary. During: decisions and actions. After: actions followed to completion.</span>} />
      <Load query={meetings} what="The review meetings" rows={6}>
        {(rows) => (
          <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
            <div className="min-w-0 space-y-5">
              {rows.length > 1 ? (
                <Select
                  label="Meeting"
                  className="w-full sm:w-96"
                  value={selected?.id ?? ''}
                  onValueChange={(value) => void navigate({ search: { meeting: value }, replace: true })}
                  options={rows.map((meeting) => ({ value: meeting.id, label: `${meeting.title} · ${formatDate(meeting.meeting_date)}` }))}
                />
              ) : null}
              {selected ? (
                <MeetingCard key={selected.id} meeting={selected} onOpenSheet={openSheet} sheetId={search.sheet} />
              ) : (
                <EmptyCard
                  title="No review meeting yet"
                  description={can('manage_actions') ? 'Create one for the period under review. Sheets prepared for that period are attached to it.' : 'Your role cannot create a meeting; the server decides who may.'}
                />
              )}
              {loose.length > 0 ? (
                <Card>
                  <CardHeader as="h2" title="Review sheets not yet on an agenda" />
                  <ul className="border-t border-ink">
                    {loose.map((row) => (
                      <li key={row.id} className="border-b border-hairline last:border-b-0">
                        <button type="button" aria-pressed={row.id === search.sheet} onClick={() => openSheet(row.id)} className="flex min-h-[34px] w-full items-center justify-between gap-4 px-4 py-1.5 text-left text-body t-colors hover:bg-hover aria-pressed:bg-cobalt-bg last:rounded-b-md">
                          <span className="font-medium text-ink">
                            {row.borrower_name} <span className="font-regular text-ink-500">· {quarterLabel(row.period_end)}</span>
                          </span>
                          <StatusDot tone={row.status === 'draft' ? 'attention' : 'pass'}>{row.status === 'draft' ? 'Draft, not yet approved' : humanize(row.status)}</StatusDot>
                        </button>
                      </li>
                    ))}
                  </ul>
                </Card>
              ) : null}
            </div>
            <div className="min-w-0">{can('manage_actions') && periods.length > 0 ? <NewMeeting periods={periods} /> : null}</div>
          </div>
        )}
      </Load>
      {search.sheet ? sheet.error ? <ErrorNotice error={sheet.error} what="The review sheet" onRetry={() => void sheet.refetch()} /> : sheet.data ? <Sheet sheet={sheet.data} /> : null : null}
      <Actions meetingId={selected?.id} />
      <p className="text-caption text-ink-500">
        Commentary drafted by an agent is marked as a draft until a person approves it. Figures in commentary are stored facts: each opens its source. Textual notes from the meeting are
        not captured here yet.
      </p>
    </div>
  );
}
