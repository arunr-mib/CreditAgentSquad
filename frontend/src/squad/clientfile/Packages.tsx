import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { API, ApiError, errorMessage, get, post } from '@/api/client';
import { useCycles } from '@/api/hooks';
import { useAuth } from '@/auth/context';
import { Button, Card, CardHeader, formatDate, Select, StatusDot } from '@/design';
import { formatTimestamp, humanize, periodEnded, periodOption } from '@/domain/labels';
import { cx } from '@/lib/cx';
import type { BorrowerRow } from '@/api/schema';
import { usePresence } from '../presence/Presence';
import { EmptyCard, Load, Notice } from '@/screens/parts';
import { PackageSchedules } from './PackageSchedules';

interface PackageFile {
  format: string;
  name: string;
  sha256: string;
  size: number;
  facts_used: number;
}

interface PackageRow {
  id: string;
  title: string;
  scope: string;
  period_end: string;
  status: 'draft' | 'generated' | 'released';
  created_at: string;
  released_at: string | null;
  files: PackageFile[];
  snapshot?: { id: string; sha256: string; as_of: string; facts: number; derived: number };
  draft_commentary?: string[];
  can_release?: boolean;
}

interface VerifyReport {
  ok: boolean;
  figures_checked: number;
  snapshot_sha256: string | null;
  problems: Array<{ file: string; where: string; figure: string; reason: string }>;
}

const FORMATS: Array<{ id: string; label: string }> = [
  { id: 'docx', label: 'Word' },
  { id: 'xlsx', label: 'Excel' },
  { id: 'pptx', label: 'PowerPoint' },
];
const FORMAT_LABEL: Record<string, string> = Object.fromEntries(FORMATS.map((format) => [format.id, format.label]));

function refusal(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) return 'Your role cannot do this';
  if (error instanceof ApiError && error.status === 409) return 'Release refused';
  return 'Not done';
}

function PackageCard({ item }: { item: PackageRow }) {
  const client = useQueryClient();
  const { say } = usePresence();
  const { can } = useAuth();
  const verify = useMutation({ mutationFn: () => post<VerifyReport>(`/packages/${item.id}/verify`) });
  const release = useMutation({
    mutationFn: () => post<PackageRow>(`/packages/${item.id}/release`),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['packages'] });
      void client.invalidateQueries({ queryKey: ['ledger'] });
      say('Package released · the snapshot is frozen · recorded');
    },
  });
  const released = item.status === 'released';
  return (
    <Card data-package={item.id}>
      <CardHeader
        as="h3"
        eyebrow={`${item.scope === 'borrower' ? 'Client' : humanize(item.scope)} package · ${periodEnded(item.period_end)}`}
        title={item.title}
        meta={
          <>
            Prepared {formatTimestamp(item.created_at)} UTC
            {item.snapshot ? (
              <>
                {' '}
                · snapshot <span className="ident">{item.snapshot.sha256.slice(0, 10)}</span> holding <span className="tnum">{item.snapshot.facts.toLocaleString('en-US')}</span> stored facts and <span className="tnum">{item.snapshot.derived.toLocaleString('en-US')}</span> figures calculated from them, as of {formatDate(item.snapshot.as_of)}
              </>
            ) : null}
          </>
        }
        actions={
          released ? (
            <StatusDot tone="pass">Released{item.released_at ? ` ${formatDate(item.released_at)}` : ''}</StatusDot>
          ) : (
            <StatusDot tone="attention">{item.draft_commentary?.length ? 'Not released: commentary is a draft' : 'Generated, not released'}</StatusDot>
          )
        }
      />
      <ul className="border-t border-ink">
        {item.files.map((file) => (
          <li key={file.name} className="grid min-h-[34px] grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-0.5 border-b border-hairline px-4 py-1.5 text-body sm:grid-cols-[110px_minmax(0,1fr)_auto_auto]">
            <span className="font-medium text-ink">{FORMAT_LABEL[file.format] ?? file.format}</span>
            <span className="ident min-w-0 break-all text-ink-700 max-sm:col-span-2 max-sm:row-start-2">{file.name}</span>
            <span className="text-caption text-ink-500 max-sm:col-span-2 max-sm:row-start-3">
              <span className="tnum">{file.facts_used.toLocaleString('en-US')}</span> of the snapshot’s facts and calculated figures cited · <span className="ident">{file.sha256.slice(0, 10)}</span>
            </span>
            <a href={`${API}/packages/${item.id}/files/${encodeURIComponent(file.name)}`} className="link font-medium" aria-label={`Download ${file.name}`} download>
              Download
            </a>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="min-w-0 text-body" aria-live="polite" data-verify-result>
          {verify.isPending ? (
            <StatusDot tone="neutral">Reopening the files</StatusDot>
          ) : verify.data ? (
            verify.data.ok ? (
              <StatusDot tone="pass" emphasis>
                Verified: all <span className="tnum">{verify.data.figures_checked.toLocaleString('en-US')}</span> figures printed in the files trace to the snapshot. A fact printed in more than one place is counted each time.
              </StatusDot>
            ) : (
              <StatusDot tone="attention" emphasis>
                <span className="tnum">{verify.data.problems.length}</span> of <span className="tnum">{verify.data.figures_checked.toLocaleString('en-US')}</span> figures printed in the files do not trace to the snapshot
              </StatusDot>
            )
          ) : (
            <span className="text-ink-500">Verification reopens every file and checks each figure against the snapshot.</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={verify.isPending} onClick={() => verify.mutate()}>
            Verify the files
          </Button>
          {!released && can('release_package') ? (
            <Button variant="primary" disabled={release.isPending} onClick={() => release.mutate()}>
              {release.isPending ? 'Releasing' : 'Release'}
            </Button>
          ) : null}
        </div>
      </div>
      {verify.data && !verify.data.ok ? (
        <ul className="border-t border-hairline px-4 py-2 text-body text-ink-700">
          {verify.data.problems.slice(0, 20).map((problem, index) => (
            <li key={index} className={cx('py-1', index > 0 && 'border-t border-hairline')}>
              <span className="ident">{problem.file}</span>, {problem.where}: “{problem.figure}” {problem.reason}
            </li>
          ))}
        </ul>
      ) : null}
      {verify.error || release.error ? (
        <div className="border-t border-hairline px-4 py-3">
          <Notice tone="attention" title={refusal(verify.error ?? release.error)}>
            The server said: “{errorMessage(verify.error ?? release.error)}”
          </Notice>
        </div>
      ) : null}
      {!released && !can('release_package') ? <p className="border-t border-hairline px-4 py-2 text-caption text-ink-500">Your role cannot release a package; the server would refuse it.</p> : null}
    </Card>
  );
}

/** Published packages for one borrower: prepare, download, verify against the snapshot, release. */
export function Packages({ borrower }: { borrower: BorrowerRow }) {
  const client = useQueryClient();
  const { say } = usePresence();
  const packages = useQuery({ queryKey: ['packages', borrower.id], queryFn: () => get<PackageRow[]>('/packages', { borrower_id: borrower.id }) });
  const cycles = useCycles({ borrower_id: borrower.id });
  const periods = (cycles.data ?? []).map((cycle) => cycle.period_end);
  const [period, setPeriod] = useState('');
  const [formats, setFormats] = useState<string[]>(FORMATS.map((format) => format.id));
  const chosen = period || periods[0] || '';
  const create = useMutation({
    mutationFn: () => post<PackageRow>('/packages', { scope: 'borrower', borrower_id: borrower.id, period_end: chosen, formats }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['packages'] });
      say('Package prepared · nothing is released yet');
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (chosen && formats.length > 0) create.mutate();
  }

  return (
    <div data-ready={packages.data ? '' : undefined} className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section aria-labelledby="packages-heading" className="min-w-0 space-y-4">
        <h2 id="packages-heading" className="text-title font-semibold text-ink">
          Packages
        </h2>
        <Load query={packages} what="The packages" rows={4}>
          {(rows) =>
            rows.length === 0 ? (
              <EmptyCard title={`No package has been prepared for ${borrower.name}`} description="A package is a set of Word, Excel and PowerPoint files built from stored facts, with a snapshot that freezes every fact behind them." />
            ) : (
              <>
                {rows.map((item) => (
                  <PackageCard key={item.id} item={item} />
                ))}
              </>
            )
          }
        </Load>
      </section>
      <Card>
        <CardHeader as="h2" title="Prepare a package" meta="Code builds the files from stored facts. Releasing is a separate step, decided by a person." />
        <form onSubmit={submit} className="space-y-3 border-t border-hairline px-4 pt-3 pb-4">
          {periods.length > 0 ? (
            <Select label="Period" value={chosen} onValueChange={setPeriod} options={periods.map((value) => ({ value, label: periodOption(value) }))} />
          ) : (
            <p className="text-body text-ink-700">No monitoring cycle exists for this client yet.</p>
          )}
          <fieldset>
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
          </fieldset>
          {create.error ? (
            <Notice tone="attention" title={create.error instanceof ApiError && create.error.status === 403 ? 'Your role cannot prepare a package' : 'The package was not prepared'}>
              The server said: “{errorMessage(create.error)}”
            </Notice>
          ) : null}
          <Button type="submit" variant="primary" disabled={create.isPending || !chosen || formats.length === 0}>
            {create.isPending ? 'Preparing' : 'Prepare the package'}
          </Button>
        </form>
      </Card>
      <div className="mt-3 min-w-0 xl:col-span-2">
        <PackageSchedules borrowerId={borrower.id} borrowerName={borrower.name} />
      </div>
    </div>
  );
}
