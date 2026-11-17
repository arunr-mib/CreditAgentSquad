import { Link } from '@tanstack/react-router';
import { useBorrower, useBorrowerCovenants, useBorrowerOverview, useDocuments, useFactsById, useSignals, useWorkItems } from '@/api/hooks';
import { Card, CardHeader, formatDate, StatusDot } from '@/design';
import { docTypeLabel, humanize, itemTypeLabel, isBreachItem, OUTCOME, quarterLabel, SEVERITY_RANK, signalLabel } from '@/domain/labels';
import { FactFigure } from '@/source/figures';
import { Def, ErrorNotice, Load, SeverityDot } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';
import { CycleStepper } from './Covenants';
import { basisFactIds, SignalBasis } from './Signals';

const rowClass = 'flex min-h-[34px] items-center justify-between gap-4 border-b border-hairline px-4 py-1.5 text-body last:border-b-0';
const more = 'link text-caption font-medium';

export function Summary() {
  const borrower = useCurrentBorrower();
  const overview = useBorrowerOverview(borrower.id);
  const detail = useBorrower(borrower.id);
  const covenants = useBorrowerCovenants(borrower.id);
  const items = useWorkItems({ status: 'open', borrower_id: borrower.id });
  const signals = useSignals({ status: 'open', borrower_id: borrower.id });
  const documents = useDocuments(borrower.id);
  const topSignals = [...(signals.data ?? [])].sort((a, b) => b.period_end.localeCompare(a.period_end) || SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]).slice(0, 5);
  const signalFacts = useFactsById(topSignals.flatMap((signal) => basisFactIds(signal.basis)));

  if (overview.error) return <ErrorNotice error={overview.error} what="The borrower summary" onRetry={() => void overview.refetch()} />;
  const cycle = overview.data?.cycle;
  const period = cycle?.period_end;
  const tests = (covenants.data?.tests ?? []).filter((test) => test.period_end === period).sort((a, b) => OUTCOME[a.outcome].rank - OUTCOME[b.outcome].rank);
  const facts = covenants.data?.facts ?? {};
  const profile = detail.data?.profile;

  return (
    <div data-ready={overview.data ? '' : undefined} className="space-y-5">
      {cycle ? <CycleStepper cycle={cycle} /> : null}
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
        <div className="min-w-0 space-y-5">
          <Card>
            <CardHeader
              as="h2"
              title="Covenants"
              meta={period ? `${quarterLabel(period)}, calculated by code` : 'No period tested'}
              actions={
                <Link to="/borrowers/$code/covenants" params={{ code: borrower.code }} className={more}>
                  Open the covenant workspace
                </Link>
              }
            />
            <Load query={covenants} what="The covenant tests" rows={3}>
              {() =>
                tests.length === 0 ? (
                  <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">No covenant has been tested for this period yet. An earlier stage is waiting for a person.</p>
                ) : (
                  <table className="w-full border-separate border-spacing-0 text-body">
                    <caption className="sr-only">Covenant tests for the latest period</caption>
                    <thead>
                      <tr>
                        {['Covenant', 'Calculated', 'Threshold', 'Headroom', 'Outcome'].map((head, index) => (
                          <th key={head} scope="col" className={`eyebrow h-8 border-t border-b border-t-hairline-strong border-b-ink px-4 ${index > 0 && index < 4 ? 'text-right' : 'text-left'}`}>
                            {head}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tests.map((test) => (
                        <tr key={test.id}>
                          <th scope="row" className="h-[34px] border-b border-hairline px-4 text-left font-medium text-ink">
                            <Link to="/borrowers/$code/covenants" params={{ code: borrower.code }} search={{ test: test.id }} className="hover:text-cobalt-strong hover:underline">
                              {test.covenant_name}
                            </Link>
                          </th>
                          <td className="border-b border-hairline px-4 text-right">
                            <FactFigure fact={test.value_fact_id ? facts[test.value_fact_id] : undefined} weight="semibold" absent="Not calculated" />
                          </td>
                          <td className="border-b border-hairline px-4 text-right">
                            <span className="mr-1.5 text-ink-500" role="img" aria-label={test.operator === '>=' ? 'at least' : 'at most'}>
                              {test.operator === '>=' ? '≥' : '≤'}
                            </span>
                            <FactFigure fact={test.threshold_fact_id ? facts[test.threshold_fact_id] : undefined} />
                          </td>
                          <td className="border-b border-hairline px-4 text-right">
                            <FactFigure fact={test.headroom_fact_id ? facts[test.headroom_fact_id] : undefined} />
                          </td>
                          <td className="border-b border-hairline px-4">
                            <StatusDot tone={OUTCOME[test.outcome].tone} emphasis={OUTCOME[test.outcome].emphasis}>
                              {OUTCOME[test.outcome].label}
                            </StatusDot>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              }
            </Load>
          </Card>

          <Card>
            <CardHeader
              as="h2"
              title="Open signals"
              meta={signals.data ? `${signals.data.length} open, latest period first` : undefined}
              actions={
                <Link to="/borrowers/$code/signals" params={{ code: borrower.code }} className={more}>
                  All signals
                </Link>
              }
            />
            <Load query={signals} what="The signals" rows={3}>
              {(rows) =>
                rows.length === 0 ? (
                  <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">No early warning signal is open.</p>
                ) : (
                  <ul className="border-t border-ink">
                    {topSignals.map((signal) => (
                      <li key={signal.id} className={rowClass}>
                        <span className="flex min-w-0 items-baseline gap-3">
                          <SeverityDot severity={signal.severity} />
                          <span className="font-medium text-ink">
                            {signalLabel(signal.rule_id)}
                            {typeof signal.basis.covenant_id === 'string' ? <span className="font-regular text-ink-500"> · {humanize(signal.basis.covenant_id)}</span> : null}
                          </span>
                          <span className="tnum text-caption text-ink-500">{quarterLabel(signal.period_end)}</span>
                        </span>
                        <span className="shrink-0 text-right">
                          <SignalBasis signal={signal} facts={signalFacts.data ?? {}} code={borrower.code} />
                        </span>
                      </li>
                    ))}
                  </ul>
                )
              }
            </Load>
          </Card>
        </div>

        <div className="min-w-0 space-y-5">
          <Card>
            <CardHeader as="h2" title="Needs a person" meta={items.data ? `${items.data.length} open ${items.data.length === 1 ? 'item' : 'items'}` : undefined} />
            <Load query={items} what="The open items" rows={2}>
              {(rows) =>
                rows.length === 0 ? (
                  <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">Nothing is waiting for a decision on this borrower.</p>
                ) : (
                  <ul className="border-t border-ink">
                    {rows.map((item) => (
                      <li key={item.id} className="border-b border-hairline last:border-b-0">
                        <Link to="/command-centre" search={{ item: item.id }} className="block px-4 py-2 t-colors hover:bg-hover last:rounded-b-md">
                          <span className="flex items-center justify-between gap-3 text-caption">
                            <SeverityDot severity={item.severity} />
                            <span className="text-ink-500">Open in the queue</span>
                          </span>
                          <span className="mt-0.5 block text-body font-medium text-pretty text-ink">{item.question}</span>
                          <span className="mt-0.5 block text-caption">
                            {isBreachItem(item.item_type) ? (
                              <StatusDot tone="breach" emphasis>
                                {itemTypeLabel(item.item_type)}
                              </StatusDot>
                            ) : (
                              <span className="text-ink-500">{itemTypeLabel(item.item_type)}</span>
                            )}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )
              }
            </Load>
          </Card>

          <Card>
            <CardHeader as="h2" title="Profile" />
            <dl className="border-t border-hairline px-4 pb-2">
              <Def label="Legal form">{profile?.legal_form ? profile.legal_form.charAt(0).toUpperCase() + profile.legal_form.slice(1) : 'Not recorded'}</Def>
              <Def label="Chief financial officer">{profile?.chief_financial_officer ?? 'Not recorded'}</Def>
              <Def label="Auditor">{profile?.auditor ?? 'Not recorded'}</Def>
              <Def label="Statements reported in">{profile?.statement_scale === 1000 ? 'Thousands of US dollars' : 'Whole US dollars'}</Def>
              <Def label="Loans">
                <Link to="/borrowers/$code/loans" params={{ code: borrower.code }} className="link">
                  {detail.data ? `${detail.data.facilities.length} on record` : 'Open'}
                </Link>
              </Def>
            </dl>
          </Card>

          <Card>
            <CardHeader
              as="h2"
              title="Latest documents"
              actions={
                <Link to="/borrowers/$code/documents" params={{ code: borrower.code }} className={more}>
                  All documents
                </Link>
              }
            />
            <Load query={documents} what="The documents" rows={3}>
              {(rows) =>
                rows.length === 0 ? (
                  <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">No document is on file.</p>
                ) : (
                  <ul className="border-t border-ink">
                    {rows.slice(0, 5).map((doc) => (
                      <li key={doc.id} className="border-b border-hairline last:border-b-0">
                        <Link to="/borrowers/$code/documents/$documentId" params={{ code: borrower.code, documentId: doc.id }} className="flex min-h-[34px] items-baseline justify-between gap-4 px-4 py-1.5 text-body t-colors hover:bg-hover last:rounded-b-md">
                          <span className="text-ink">
                            {docTypeLabel(doc.doc_type)}
                            {doc.period_end ? <span className="text-ink-500"> · {quarterLabel(doc.period_end)}</span> : null}
                          </span>
                          <span className="tnum shrink-0 text-caption text-ink-500">{doc.received_date ? formatDate(doc.received_date) : 'Not dated'}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )
              }
            </Load>
          </Card>
        </div>
      </div>
    </div>
  );
}
