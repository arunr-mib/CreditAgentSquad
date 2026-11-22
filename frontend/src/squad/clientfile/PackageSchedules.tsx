import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent } from 'react';
import { get, post } from '@/api/client';
import { useAuth } from '@/auth/context';
import { Button, Card, CardHeader, formatDate, Input, Select, StatusDot } from '@/design';
import { quarterLabel } from '@/domain/labels';
import { Refusal } from '@/repair/FigureForm';
import { Load } from '@/screens/parts';

/** A row of GET /package-schedules. */
export interface PackageSchedule {
  id: string;
  title: string;
  scope: 'borrower' | 'portfolio' | string;
  borrower_id: string | null;
  cadence: 'monthly' | 'quarterly' | string;
  days_after_period_end: number;
  formats: string[];
  active: boolean;
  next_run: string | null;
}

/** The answer of POST /package-schedules/run. */
export interface ScheduleRunReport {
  today: string;
  runs: Array<{ schedule_id: string; period_end: string; package_id: string | null; error: string | null; next_run: string | null }>;
}

const FORMATS: Array<{ id: string; label: string }> = [
  { id: 'docx', label: 'Word' },
  { id: 'xlsx', label: 'Excel' },
  { id: 'pptx', label: 'PowerPoint' },
];
const FORMAT_LABEL: Record<string, string> = Object.fromEntries(FORMATS.map((format) => [format.id, format.label]));
const CADENCE: Record<string, string> = { quarterly: 'Quarterly', monthly: 'Monthly' };

/** What one run of the due schedules did, in words. Nothing is claimed that the server did not report. */
export function runSentences(report: ScheduleRunReport, titles: Record<string, string>): Array<{ tone: 'neutral' | 'attention'; text: string }> {
  if (report.runs.length === 0) return [{ tone: 'neutral', text: `No schedule was due on ${formatDate(report.today)}. Nothing was generated.` }];
  return report.runs.map((run) => {
    const name = titles[run.schedule_id] ?? 'A schedule';
    const period = quarterLabel(run.period_end);
    if (run.error) return { tone: 'attention', text: `${name}, ${period}: not generated. The server said: “${run.error}” The schedule stays due and will be tried again.` };
    return { tone: 'neutral', text: `${name}, ${period}: a package was prepared, not released.${run.next_run ? ` Next run ${formatDate(run.next_run)}.` : ''}` };
  });
}

function NewSchedule({ borrowerId, borrowerName }: { borrowerId: string; borrowerName: string }) {
  const client = useQueryClient();
  const formatsNote = useId();
  const [title, setTitle] = useState('');
  const [scope, setScope] = useState('borrower');
  const [cadence, setCadence] = useState('quarterly');
  const [days, setDays] = useState('60');
  const [formats, setFormats] = useState<string[]>(FORMATS.map((format) => format.id));
  const [firstRun, setFirstRun] = useState('');
  const [problems, setProblems] = useState<{ title?: string; days?: string; formats?: string }>({});
  const create = useMutation({
    mutationFn: () =>
      post<PackageSchedule>('/package-schedules', {
        title: title.trim(),
        scope,
        borrower_id: scope === 'borrower' ? borrowerId : null,
        cadence,
        days_after_period_end: Number.parseInt(days, 10),
        formats,
        next_run: firstRun || null,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['package-schedules'] });
      void client.invalidateQueries({ queryKey: ['ledger'] });
      setTitle('');
      setFirstRun('');
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const next: typeof problems = {};
    if (!title.trim()) next.title = 'Give the schedule a title.';
    if (!/^\d+$/.test(days.trim())) next.days = 'Enter a whole number of days, zero or more.';
    if (formats.length === 0) next.formats = 'Choose at least one file.';
    setProblems(next);
    if (Object.keys(next).length === 0) create.mutate();
  }

  return (
    <Card>
      <CardHeader as="h2" title="New schedule" meta="A scheduled package is prepared when it falls due. Releasing it stays a decision for a person." />
      <form onSubmit={submit} noValidate aria-label="New package schedule" className="space-y-3 border-t border-hairline px-4 pt-3 pb-4">
        <Input label="Title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Quarterly review package" error={problems.title} />
        <Select
          label="For"
          value={scope}
          onValueChange={setScope}
          options={[
            { value: 'borrower', label: borrowerName },
            { value: 'portfolio', label: 'The whole portfolio' },
          ]}
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Select label="How often" value={cadence} onValueChange={setCadence} options={Object.entries(CADENCE).map(([value, label]) => ({ value, label }))} />
          <Input label="Days after period end" inputMode="numeric" value={days} onChange={(event) => setDays(event.target.value)} error={problems.days} />
        </div>
        <fieldset aria-describedby={problems.formats ? formatsNote : undefined}>
          <legend className="mb-1 text-caption font-medium text-ink-700">Files</legend>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {FORMATS.map((format) => (
              <label key={format.id} className="inline-flex items-center gap-1.5 text-body text-ink">
                <input
                  type="checkbox"
                  className="size-3.5 accent-cobalt"
                  checked={formats.includes(format.id)}
                  onChange={(event) => setFormats((list) => (event.target.checked ? [...list, format.id] : list.filter((id) => id !== format.id)))}
                />
                {format.label}
              </label>
            ))}
          </div>
          {problems.formats ? (
            <p id={formatsNote} className="mt-1 text-caption font-medium text-amber">
              {problems.formats}
            </p>
          ) : null}
        </fieldset>
        <Input label="First run (optional)" type="date" value={firstRun} onChange={(event) => setFirstRun(event.target.value)} hint="Left empty, the server takes the first date on or after today when a period falls due." />
        {create.error ? <Refusal error={create.error} outcome="Not created" /> : null}
        <div aria-live="polite" className="text-body text-ink-700" data-schedule-created>
          {create.data ? (
            <>
              Created: {create.data.title}
              {create.data.next_run ? `, first run ${formatDate(create.data.next_run)}` : ''}. It is in the ledger.
            </>
          ) : null}
        </div>
        <Button type="submit" variant="primary" disabled={create.isPending}>
          {create.isPending ? 'Creating' : 'Create the schedule'}
        </Button>
      </form>
    </Card>
  );
}

/**
 * Package schedules, where packages are listed: the schedules that cover this client (its own
 * and the portfolio's), a way to create one, and a way to run whatever has fallen due now.
 */
export function PackageSchedules({ borrowerId, borrowerName }: { borrowerId: string; borrowerName: string }) {
  const client = useQueryClient();
  const { can } = useAuth();
  const schedules = useQuery({ queryKey: ['package-schedules'], queryFn: () => get<PackageSchedule[]>('/package-schedules') });
  const run = useMutation({
    mutationFn: () => post<ScheduleRunReport>('/package-schedules/run'),
    onSuccess: () => {
      for (const key of ['package-schedules', 'packages', 'ledger']) void client.invalidateQueries({ queryKey: [key] });
    },
  });
  const allowed = can('release_package');
  const titles = Object.fromEntries((schedules.data ?? []).map((row) => [row.id, row.title]));

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]" data-package-schedules>
      <section aria-labelledby="schedules-heading" className="min-w-0">
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <div className="flex items-baseline gap-x-3 max-sm:flex-wrap">
            <h2 id="schedules-heading" className="text-title font-semibold text-ink">
              Schedules
            </h2>
            <p className="text-caption text-ink-500">Packages prepared by code when a period’s package falls due</p>
          </div>
          {allowed ? (
            <Button disabled={run.isPending} onClick={() => run.mutate()}>
              {run.isPending ? 'Running' : 'Run schedules that are due'}
            </Button>
          ) : null}
        </div>
        <Load query={schedules} what="The package schedules" rows={3}>
          {(rows) => {
            const here = rows.filter((row) => row.scope === 'portfolio' || row.borrower_id === borrowerId);
            const elsewhere = rows.length - here.length;
            return (
              <Card>
                {here.length === 0 ? (
                  <p className="px-4 py-3 text-body text-pretty text-ink-700">No schedule covers {borrowerName} yet. Packages are prepared only when someone asks for one above.</p>
                ) : (
                  <table className="stack-narrow w-full border-separate border-spacing-0 text-body">
                    <caption className="sr-only">Package schedules that cover this client</caption>
                    <thead>
                      <tr>
                        {['Schedule', 'For', 'How often', 'Due', 'Files', 'Next run'].map((head) => (
                          <th key={head} scope="col" className="eyebrow h-8 border-b border-ink px-4 text-left whitespace-nowrap">
                            {head}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {here.map((row) => (
                        <tr key={row.id} data-schedule={row.id}>
                          <th scope="row" className="h-[34px] border-b border-hairline px-4 py-1.5 text-left font-medium text-ink">
                            {row.title}
                          </th>
                          <td data-label="For" className="border-b border-hairline px-4 py-1.5 whitespace-nowrap text-ink-700">{row.scope === 'portfolio' ? 'The whole portfolio' : 'This client'}</td>
                          <td data-label="How often" className="border-b border-hairline px-4 py-1.5 whitespace-nowrap text-ink-700">{CADENCE[row.cadence] ?? row.cadence}</td>
                          <td data-label="Due" className="border-b border-hairline px-4 py-1.5 whitespace-nowrap text-ink-700">
                            <span className="tnum">{row.days_after_period_end}</span> {row.days_after_period_end === 1 ? 'day' : 'days'} after period end
                          </td>
                          <td data-label="Files" className="border-b border-hairline px-4 py-1.5 text-ink-700">{row.formats.map((format) => FORMAT_LABEL[format] ?? format).join(', ')}</td>
                          <td data-label="Next run" className="border-b border-hairline px-4 py-1.5 whitespace-nowrap">
                            {!row.active ? <StatusDot tone="muted">Paused</StatusDot> : row.next_run ? <span className="tnum text-ink">{formatDate(row.next_run)}</span> : <span className="text-ink-500">Not set</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {elsewhere > 0 ? (
                  <p className="border-t border-hairline px-4 py-2 text-caption text-ink-500">
                    <span className="tnum">{elsewhere}</span> more {elsewhere === 1 ? 'schedule is' : 'schedules are'} for other clients and {elsewhere === 1 ? 'is' : 'are'} listed in their client files.
                  </p>
                ) : null}
              </Card>
            );
          }}
        </Load>
        <div aria-live="polite" data-schedule-run className="mt-2">
          {run.data ? (
            <ul className="space-y-1 text-body text-pretty">
              {runSentences(run.data, titles).map((line) => (
                <li key={line.text}>
                  <StatusDot tone={line.tone} className="whitespace-normal!">
                    {line.text}
                  </StatusDot>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        {run.error ? <Refusal error={run.error} outcome="Not run" className="mt-2" /> : null}
        <p className="mt-2 text-caption text-pretty text-ink-500">
          {allowed
            ? 'Running prepares the package for every schedule that has fallen due on the workspace’s date, for any client, once; a schedule that is not due is left alone.'
            : 'Your role can read package schedules but cannot create or run them; the server decides who may.'}
        </p>
      </section>
      {allowed ? <NewSchedule borrowerId={borrowerId} borrowerName={borrowerName} /> : null}
    </div>
  );
}
