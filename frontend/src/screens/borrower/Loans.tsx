import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useBorrowerOverview, useBorrowerTerms, useWorkItems } from '@/api/hooks';
import type { Citation, LoanTerms, TermsVersionRow } from '@/api/schema';
import { Button, Card, CardHeader, formatDate, formatFigure, StatusDot, type StatusTone } from '@/design';
import { docTypeLabel, humanize } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { useSource } from '@/source/context';
import { FactFigure, SourcedFigure } from '@/source/figures';
import { EmptyCard, Load, Notice } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';

const VERSION_STATUS: Record<TermsVersionRow['status'], { tone: StatusTone; label: string }> = {
  approved: { tone: 'neutral', label: 'Approved' },
  proposed: { tone: 'attention', label: 'Proposed, does not govern' },
  superseded: { tone: 'muted', label: 'Superseded' },
  rejected: { tone: 'muted', label: 'Rejected' },
};
const LOAN_TYPE: Record<string, string> = { revolver: 'Line of credit', term_loan: 'Term loan' };

function Clause({ citation, code, children }: { citation: Citation | null | undefined; code: string; children: string }) {
  const source = useSource();
  if (!citation?.document_id || !citation.page) return <span className="text-ink-500">{children}</span>;
  return (
    <button
      type="button"
      className="link"
      onClick={() => source.open({ type: 'document', documentId: citation.document_id as string, page: citation.page as number, quote: citation.quote, section: citation.section, title: citation.document_title ?? 'Credit agreement', borrowerCode: code })}
    >
      {children}
    </button>
  );
}

function Version({ version, code }: { version: TermsVersionRow; code: string }) {
  const [open, setOpen] = useState(version.in_force);
  const status = VERSION_STATUS[version.status];
  const panel = `terms-${version.id}`;
  return (
    <li className="border-b border-hairline last:border-b-0">
      <div className="grid min-h-[38px] grid-cols-[88px_minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1.6fr)_auto] items-center gap-x-4 px-4 py-1.5 text-body">
        <span className="font-semibold text-ink">
          Version <span className="tnum">{version.version}</span>
        </span>
        <span>
          {version.in_force ? (
            <StatusDot tone="neutral">
              <span className="font-semibold">In force</span>
            </StatusDot>
          ) : (
            <StatusDot tone={status.tone} emphasis={version.status === 'proposed'}>
              {status.label}
            </StatusDot>
          )}
        </span>
        <span className="tnum text-ink-700">
          {formatDate(version.effective_from)} to {version.effective_to ? formatDate(version.effective_to) : 'open-ended'}
        </span>
        <span className="text-ink-700">
          {version.approved_by_name ? `Approved by ${version.approved_by_name}${version.approved_at ? `, ${formatDate(version.approved_at)}` : ''}` : 'Not approved by a second person'}
        </span>
        <Button size="sm" variant="ghost" aria-expanded={open} aria-controls={panel} onClick={() => setOpen(!open)}>
          {open ? 'Hide the terms' : 'Show the terms'}
        </Button>
      </div>
      {open ? (
        <div id={panel} className="border-t border-hairline bg-canvas px-4 pt-3 pb-4">
          <p className="text-caption text-ink-500">
            Prepared by {version.prepared_by_id || humanize(version.prepared_by_type)} · from{' '}
            {version.source_documents.length > 0
              ? version.source_documents.map((doc, index) => (
                  <span key={doc.reference}>
                    {index > 0 ? ', ' : ''}
                    {doc.id ? (
                      <Link to="/borrowers/$code/documents/$documentId" params={{ code, documentId: doc.id }} className="link">
                        {docTypeLabel(doc.doc_type)}
                      </Link>
                    ) : (
                      doc.title
                    )}
                  </span>
                ))
              : 'no source document recorded'}
            {version.warnings && version.warnings.length > 0 ? ` · ${version.warnings.length} provenance warnings` : version.warnings ? ' · every citation was found on its page' : ' · citations not yet checked'}
          </p>
          <div className="mt-2 grid gap-5 xl:grid-cols-2">
            <table className="w-full self-start text-body">
              <caption className="eyebrow pb-1 text-left">Financial covenants</caption>
              <thead>
                <tr className="text-left">
                  <th scope="col" className="eyebrow border-b border-ink py-1 font-semibold">
                    Covenant
                  </th>
                  <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                    Threshold
                  </th>
                  <th scope="col" className="eyebrow border-b border-ink py-1 pl-4 font-semibold">
                    Tested
                  </th>
                  <th scope="col" className="eyebrow border-b border-ink py-1 pl-4 font-semibold">
                    Clause
                  </th>
                </tr>
              </thead>
              <tbody>
                {version.covenants.map((covenant) => {
                  const citation = covenant.citations.find((entry) => entry?.field?.startsWith('test')) ?? covenant.citations[0];
                  const clause = citation?.document_id && citation.page ? { type: 'document' as const, documentId: citation.document_id, page: citation.page, quote: citation.quote, section: citation.section, title: citation.document_title ?? 'Credit agreement', borrowerCode: code } : null;
                  return (
                    <tr key={covenant.id} className="border-b border-hairline last:border-b-0">
                      <th scope="row" className="py-1.5 text-left font-medium text-ink">
                        {covenant.name}
                      </th>
                      <td className="py-1.5 text-right whitespace-nowrap">
                        <span className="mr-1.5 text-ink-500" role="img" aria-label={covenant.operator === '>=' ? 'at least' : 'at most'}>
                          {covenant.operator === '>=' ? '≥' : '≤'}
                        </span>
                        {clause ? (
                          <SourcedFigure value={covenant.threshold} unit={covenant.unit} kind="extracted" label={`${covenant.name}, threshold in the terms`} source={clause} scale={covenant.unit === 'usd' ? 1000 : 1} />
                        ) : (
                          <span className="tnum">{covenant.threshold ? formatFigure(covenant.threshold, covenant.unit).text : 'Not set'}</span>
                        )}
                      </td>
                      <td className="py-1.5 pl-4 text-ink-700">
                        {humanize(covenant.measurement?.frequency ?? 'quarterly')}, {covenant.measurement?.basis === 'ttm' ? 'trailing twelve months' : (covenant.measurement?.basis ?? 'at the period end')}
                        {covenant.steps.length > 0 ? `, ${covenant.steps.length} step changes` : ''}
                      </td>
                      <td className="py-1.5 pl-4">
                        <Clause citation={citation} code={code}>
                          {citation?.section ? `Section ${citation.section}` : 'Not cited'}
                        </Clause>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <table className="w-full self-start text-body">
              <caption className="eyebrow pb-1 text-left">Reporting requirements</caption>
              <thead>
                <tr className="text-left">
                  <th scope="col" className="eyebrow border-b border-ink py-1 font-semibold">
                    Document
                  </th>
                  <th scope="col" className="eyebrow border-b border-ink py-1 pl-4 font-semibold">
                    Requirement
                  </th>
                  <th scope="col" className="eyebrow border-b border-ink py-1 pl-4 font-semibold">
                    Clause
                  </th>
                </tr>
              </thead>
              <tbody>
                {version.reporting_requirements.map((requirement) => (
                  <tr key={requirement.id} className="border-b border-hairline last:border-b-0">
                    <th scope="row" className="py-1.5 text-left font-medium text-ink">
                      {docTypeLabel(requirement.document_type)}
                    </th>
                    <td className="py-1.5 pl-4 text-ink-700">
                      {humanize(requirement.id)}
                      {requirement.quality ? `, ${requirement.quality}` : ''}
                    </td>
                    <td className="py-1.5 pl-4">
                      <Clause citation={requirement.citation} code={code}>
                        {requirement.citation?.section ? `Section ${requirement.citation.section}` : 'Not cited'}
                      </Clause>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {version.addbacks.length > 0 ? (
            <p className="mt-3 text-caption text-ink-500">
              EBITDA add-backs allowed: {version.addbacks.map((addback) => humanize(String(addback.name ?? addback.id ?? 'add-back'))).join(', ')}. An add-back with no cap is uncapped.
            </p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

function LoanCard({ loan, code, outstanding }: { loan: LoanTerms; code: string; outstanding: React.ReactNode }) {
  const record = (label: string, value: string) => ({
    type: 'record' as const,
    kind: 'system' as const,
    title: `${loan.name}: ${label}`,
    value: formatFigure(value, 'usd').text,
    note: 'A field of the loan record in the system of record. It is not a spread fact, so it has no page; the credit agreement states the commitment in its own clauses.',
    rows: [
      ['System', 'Core loan accounting'],
      ['Loan record', loan.code],
    ] as Array<[string, string]>,
  });
  return (
    <Card className={cx('min-w-0')}>
      <CardHeader
        as="h2"
        eyebrow={
          <>
            {LOAN_TYPE[loan.facility_type] ?? humanize(loan.facility_type)} <span className="ident tracking-normal normal-case">{loan.code}</span>
          </>
        }
        title={loan.name}
        meta={loan.has_borrowing_base ? 'Advances are limited by a borrowing base' : undefined}
      />
      <dl className="grid grid-cols-5 divide-x divide-hairline border-t border-hairline-strong">
        {[
          ['Commitment', <SourcedFigure key="c" value={loan.commitment} unit="usd" kind="system" label={`${loan.name}, commitment`} source={record('commitment', loan.commitment)} weight="semibold" />],
          ['Outstanding', outstanding],
          ['Rate', <span key="r">{loan.profile.interest_rate ?? 'Not recorded'}</span>],
          ['Originated', <span key="o" className="tnum">{loan.origination_date ? formatDate(loan.origination_date) : 'Not recorded'}</span>],
          ['Matures', <span key="m" className="tnum">{loan.maturity_date ? formatDate(loan.maturity_date) : 'Not recorded'}</span>],
        ].map(([label, value]) => (
          <div key={label as string} className="px-4 py-2.5">
            <dt className="eyebrow">{label}</dt>
            <dd className="mt-0.5 text-body text-ink">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="border-t border-hairline-strong">
        <h3 className="eyebrow px-4 pt-3 pb-1.5">Terms versions, newest first</h3>
        {loan.terms_versions.length === 0 ? (
          <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">
            No terms are recorded for this loan. Its covenants are set in the terms of the borrower’s other loan under the same credit agreement, or have not been prepared yet.
          </p>
        ) : (
          <ul className="border-t border-ink">
            {loan.terms_versions.map((version) => (
              <Version key={version.id} version={version} code={code} />
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

export function Loans() {
  const borrower = useCurrentBorrower();
  const terms = useBorrowerTerms(borrower.id);
  const overview = useBorrowerOverview(borrower.id);
  const items = useWorkItems({ status: 'open', borrower_id: borrower.id });
  const amendment = items.data?.find((item) => item.item_type === 'terms.unapproved_amendment' || item.item_type === 'terms.approval_needed');
  const exposure = overview.data?.exposure;
  return (
    <Load query={terms} what="The loans" rows={8}>
      {(loans) =>
        loans.length === 0 ? (
          <div data-ready>
            <EmptyCard title="No loan is on record for this borrower" />
          </div>
        ) : (
          <div data-ready className="space-y-5">
            {amendment ? (
              <Notice
                tone="attention"
                title={amendment.item_type === 'terms.unapproved_amendment' ? 'An amendment is on file but is not in the approved terms' : 'Proposed terms are waiting for a second person'}
                action={
                  <Button asChild>
                    <Link to="/command-centre" search={{ item: amendment.id }}>
                      Open the item
                    </Link>
                  </Button>
                }
              >
                Covenants are tested against the approved version only. A proposed version never governs a test, and an amendment creates a new version; it never overwrites one.
              </Notice>
            ) : null}
            {loans.map((loan) => (
              <LoanCard
                key={loan.id}
                loan={loan}
                code={borrower.code}
                outstanding={
                  <FactFigure
                    fact={loan.facility_type === 'revolver' ? exposure?.revolver_outstanding : loan.facility_type === 'term_loan' ? exposure?.term_loan_outstanding : undefined}
                    weight="semibold"
                    absent="No balance on record"
                  />
                }
              />
            ))}
            <p className="text-caption text-ink-500">
              Terms are versioned and effective-dated. Each version is approved by a second person before it governs a test. Every threshold opens the clause that sets it.
            </p>
          </div>
        )
      }
    </Load>
  );
}
