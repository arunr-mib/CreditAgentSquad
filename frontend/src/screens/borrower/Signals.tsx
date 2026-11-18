import { Link } from '@tanstack/react-router';
import { Fragment, useMemo, useState, type ReactNode } from 'react';
import { mul } from '@/api/decimal';
import { useFactsById, useSignals } from '@/api/hooks';
import type { FactsById, SignalRow } from '@/api/schema';
import { AgentNote, DataTable, formatDate, Segmented, StatusDot, type DataColumn } from '@/design';
import { humanize, quarterLabel, SEVERITY_RANK, signalLabel } from '@/domain/labels';
import { AgentBody } from '@/source/AgentBody';
import { FactFigure, SourcedFigure } from '@/source/figures';
import { EmptyCard, Load, SectionHead, SeverityDot } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';

type Basis = Record<string, unknown>;
const id = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);
const nested = (basis: Basis, key: string): Basis | null => (basis[key] && typeof basis[key] === 'object' ? (basis[key] as Basis) : null);

/** Every fact a signal's basis points at, so the figures can be fetched in one go. */
export function basisFactIds(basis: Basis): string[] {
  const ids: Array<string | null> = [];
  for (const key of ['metric_fact_ids', 'system_fact_ids']) {
    const group = nested(basis, key);
    if (group) ids.push(...Object.values(group).map(id));
  }
  for (const key of ['current', 'prior', 'availability']) ids.push(id(nested(basis, key)?.fact_id));
  if (Array.isArray(basis.values)) ids.push(...basis.values.map((entry) => id((entry as Basis)?.fact_id)));
  return ids.filter((value): value is string => Boolean(value));
}

/** What the rule compared, as figures that open their sources. Day counts come from the calendar, not from facts. */
export function SignalBasis({ signal, facts, code }: { signal: SignalRow; facts: FactsById; code: string }) {
  const basis = signal.basis;
  const metric = nested(basis, 'metric_fact_ids');
  const system = nested(basis, 'system_fact_ids');
  const fact = (value: unknown) => {
    const key = id(value);
    return key ? facts[key] : undefined;
  };
  const parts: ReactNode[] = [];
  if (metric) {
    parts.push(
      <Fragment key="metric">
        <FactFigure fact={fact(metric.current)} weight="medium" /> now, <FactFigure fact={fact(metric.year_earlier)} /> a year earlier
      </Fragment>,
    );
  } else if (Array.isArray(basis.values)) {
    parts.push(
      <Fragment key="values">
        {basis.values.map((entry, index) => (
          <Fragment key={index}>
            {index > 0 ? <span className="mx-1 text-ink-500">then</span> : null}
            <FactFigure fact={fact((entry as Basis).fact_id)} weight={index === (basis.values as unknown[]).length - 1 ? 'medium' : 'regular'} />
          </Fragment>
        ))}
      </Fragment>,
    );
  } else if (nested(basis, 'current')) {
    parts.push(
      <Fragment key="current">
        <FactFigure fact={fact(nested(basis, 'current')?.fact_id)} weight="medium" /> headroom
      </Fragment>,
    );
  } else if (nested(basis, 'availability')) {
    parts.push(
      <Fragment key="availability">
        <FactFigure fact={fact(nested(basis, 'availability')?.fact_id)} weight="medium" scale={1000} /> <span className="text-ink-500">thousand available of</span>{' '}
        <FactFigure fact={fact(system?.['sys.commitment'])} scale={1000} /> <span className="text-ink-500">thousand</span>
      </Fragment>,
    );
  } else if (signal.rule_id === 'line_usage_high' && system) {
    parts.push(
      <Fragment key="usage">
        <FactFigure fact={fact(system['sys.revolver_outstanding'])} weight="medium" /> drawn of <FactFigure fact={fact(system['sys.commitment'])} />
      </Fragment>,
    );
  } else if (signal.rule_id === 'payment_past_due' && system) {
    parts.push(
      <Fragment key="pastdue">
        <FactFigure fact={fact(system['sys.past_due_days'])} weight="medium" /> past due
      </Fragment>,
    );
  } else if (typeof basis.days_late === 'number') {
    parts.push(
      <Link key="late" to="/calendar" className="link">
        {basis.days_late} days late; see the calendar
      </Link>,
    );
  }
  const change = id(basis.change);
  if (change && metric) {
    const unit = /^-?0\.\d/.test(change) && signal.rule_id !== 'leverage_increase' ? 'pct' : signal.rule_id === 'leverage_increase' ? 'ratio' : 'days';
    parts.push(
      <span key="change" className="ml-2 text-ink-500">
        change{' '}
        <SourcedFigure
          value={unit === 'pct' ? mul(change, '100') : change}
          unit={unit}
          kind="calculated"
          label={`${signalLabel(signal.rule_id)}, change`}
          source={{
            type: 'record',
            kind: 'calculated',
            title: `${signalLabel(signal.rule_id)}: change`,
            value: change,
            note: 'Computed by the signal rule from the two figures beside it. Each of those is a stored fact that opens its own source.',
            rows: [
              ['Rule', signal.rule_id],
              ['Rule version', signal.rule_version],
              ['Period', formatDate(signal.period_end)],
            ],
            link: { to: `/borrowers/${code}/spreads`, label: 'Open the spread' },
          }}
        />
      </span>,
    );
  }
  if (parts.length === 0) return <span className="text-ink-500">Basis recorded with the rule</span>;
  return <span className="text-ink-700">{parts}</span>;
}

export function Signals() {
  const borrower = useCurrentBorrower();
  const [status, setStatus] = useState('open');
  const signals = useSignals({ status: 'all', borrower_id: borrower.id });
  const ids = useMemo(() => (signals.data ?? []).flatMap((signal) => basisFactIds(signal.basis)), [signals.data]);
  const facts = useFactsById(ids);

  const columns = useMemo<Array<DataColumn<SignalRow>>>(
    () => [
      { id: 'severity', header: 'Severity', sortValue: (row) => SEVERITY_RANK[row.severity], cell: (row) => <SeverityDot severity={row.severity} /> },
      {
        id: 'rule',
        header: 'Signal',
        rowHeader: true,
        wrap: true,
        sortValue: (row) => signalLabel(row.rule_id),
        cell: (row) => {
          const subject = id(row.basis.covenant_id) ?? id(row.basis.subject);
          return (
            <span className="font-medium text-ink">
              {signalLabel(row.rule_id)}
              {subject ? <span className="font-regular text-ink-500"> · {humanize(subject)}</span> : null}
            </span>
          );
        },
      },
      { id: 'period', header: 'Period', sortValue: (row) => row.period_end, cell: (row) => <span className="tnum text-ink-700">{quarterLabel(row.period_end)}</span> },
      { id: 'basis', header: 'What the rule compared', wrap: true, width: '38%', cell: (row) => <SignalBasis signal={row} facts={facts.data ?? {}} code={borrower.code} /> },
      {
        id: 'status',
        header: 'Status',
        sortValue: (row) => row.status,
        cell: (row) => <StatusDot tone={row.status === 'open' ? 'neutral' : row.status === 'acknowledged' ? 'pass' : 'muted'}>{humanize(row.status)}</StatusDot>,
      },
    ],
    [facts.data, borrower.code],
  );

  return (
    <Load query={signals} what="The signals" rows={8}>
      {(rows) => {
        const shown = rows
          .filter((row) => status === 'all' || row.status === status)
          .sort((a, b) => b.period_end.localeCompare(a.period_end) || SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
        const explained = shown.filter((row) => row.explanation?.text);
        return (
          <section data-ready aria-labelledby="signals-heading" className="space-y-4">
            <div>
              <SectionHead
                id="signals-heading"
                title="Early warning signals"
                note="Fired by code, newest period first. An agent may explain and rank a signal; it cannot create or suppress one."
                actions={
                  <Segmented
                    label="Status"
                    value={status}
                    onValueChange={setStatus}
                    options={[
                      { value: 'open', label: 'Open', count: rows.filter((row) => row.status === 'open').length },
                      { value: 'all', label: 'All', count: rows.length },
                    ]}
                  />
                }
              />
              {shown.length === 0 ? (
                <EmptyCard title={rows.length === 0 ? 'No signal has fired for this borrower' : 'No open signal'} description="Signals are tested each period against the spread, the covenant tests, the loan system and the reporting calendar." />
              ) : (
                <DataTable caption="Early warning signals for this borrower" data={shown} columns={columns} getRowId={(row) => row.id} stickyTop="var(--topbar-h)" narrow="stack" />
              )}
            </div>
            {explained.map((row) => (
              <AgentNote key={row.id} agent="Early Warning Agent" headline={`Explains: ${signalLabel(row.rule_id)}`} state="draft">
                <AgentBody text={row.explanation?.text ?? ''} />
              </AgentNote>
            ))}
          </section>
        );
      }}
    </Load>
  );
}
