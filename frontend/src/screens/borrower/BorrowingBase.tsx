import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { useBorrowingBase } from '@/api/hooks';
import type { BorrowingBaseReview } from '@/api/schema';
import { Card, CardHeader, formatDate, Select, StatusDot, type StatusTone } from '@/design';
import { cx } from '@/lib/cx';
import { useSource, type SourceRef } from '@/source/context';
import { Absent, FactFigure, ProvenanceLegend, SourcedFigure } from '@/source/figures';
import { EmptyCard, Load, SectionHead } from '../parts';
import { WorkItemPanel } from '../work/WorkItemPanel';
import { useCurrentBorrower } from './BorrowerLayout';

const OUTCOME: Record<BorrowingBaseReview['outcome'], { tone: StatusTone; label: string; emphasis?: boolean }> = {
  agrees: { tone: 'pass', label: 'Agrees with the certificate' },
  mismatch: { tone: 'attention', label: 'Certificate differs from the recalculation', emphasis: true },
  over_advance: { tone: 'attention', label: 'Over-advanced', emphasis: true },
  cannot_compute: { tone: 'attention', label: 'Could not be recalculated' },
};
const SHORT: Record<BorrowingBaseReview['outcome'], string> = { agrees: 'Agrees', mismatch: 'Certificate differs', over_advance: 'Over-advanced', cannot_compute: 'Not recalculated' };
const STRONG = new Set(['ar_eligible', 'inventory_eligible', 'borrowing_base', 'borrowing_limit', 'availability', 'over_advance', 'ar_ineligible_total']);
const TOTAL = new Set(['availability']);

function ReviewCard({ review, code }: { review: BorrowingBaseReview; code: string }) {
  const source = useSource();
  const outcome = OUTCOME[review.outcome];
  const calc: SourceRef | null = review.calc_run_id ? { type: 'calculation', id: review.calc_run_id, title: `Borrowing base, ${formatDate(review.period_end)}` } : null;
  const certificate: SourceRef | null = review.certificate_document
    ? { type: 'document', documentId: review.certificate_document.id, page: 1, title: review.certificate_document.title, borrowerCode: code }
    : null;
  return (
    <Card className="min-w-0">
      <CardHeader
        as="h2"
        eyebrow="Borrowing base review"
        title={`As of ${formatDate(review.period_end)}`}
        meta={
          <>
            {review.loan_name ?? 'Line of credit'} · recalculated by code from the aging and inventory detail
            {certificate ? (
              <>
                {' · '}
                <button type="button" className="link" onClick={() => source.open(certificate)}>
                  The certificate
                </button>
              </>
            ) : null}
          </>
        }
        actions={
          <StatusDot tone={outcome.tone} emphasis={outcome.emphasis}>
            {outcome.label}
          </StatusDot>
        }
      />
      <table className="w-full border-separate border-spacing-0 text-body">
        <caption className="sr-only">Borrowing base as of {formatDate(review.period_end)}: each line as recalculated beside the certificate, US dollars in thousands</caption>
        <thead>
          <tr>
            <th scope="col" className="eyebrow h-8 border-t border-b border-t-hairline-strong border-b-ink px-4 text-left">
              Line
            </th>
            {['Recalculated', 'Certificate', 'Difference'].map((head) => (
              <th key={head} scope="col" className="eyebrow h-8 w-[118px] border-t border-b border-t-hairline-strong border-b-ink px-3 text-right">
                {head}
              </th>
            ))}
            <th scope="col" className="eyebrow h-8 w-[104px] border-t border-b border-t-hairline-strong border-b-ink px-3 text-left">
              Check
            </th>
          </tr>
        </thead>
        <tbody>
          {review.lines.map((line, index) => {
            const strong = STRONG.has(line.line);
            const total = TOTAL.has(line.line);
            const last = index === review.lines.length - 1;
            const cell = cx('px-3 py-1.5 text-right', !last && !total && 'border-b border-hairline', strong && 'border-t border-t-ink', total && 'border-b-[3px] border-double border-b-ink');
            const differs = line.status === 'mismatch';
            return (
              <tr key={line.line} className={cx(strong && 'bg-canvas')}>
                <th scope="row" className={cx('px-4 py-1.5 text-left', !last && 'border-b border-hairline', strong ? 'font-semibold text-ink' : 'font-regular text-ink-700')} style={{ paddingLeft: 16 + line.depth * 16 }}>
                  {line.label}
                </th>
                <td className={cell}>
                  {calc ? (
                    <SourcedFigure value={line.computed} unit="usd" kind="calculated" label={`${line.label}, recalculated`} context={`As of ${formatDate(review.period_end)}`} source={calc} scale={1000} unitMark={false} align="column" weight={strong ? 'semibold' : 'regular'} />
                  ) : (
                    <Absent align="column" reason="Not recalculated" />
                  )}
                </td>
                <td className={cell}>
                  {certificate ? (
                    <SourcedFigure value={line.certificate} unit="usd" kind="extracted" label={`${line.label}, on the certificate`} context={`As of ${formatDate(review.period_end)}`} source={certificate} scale={1000} unitMark={false} align="column" />
                  ) : (
                    <Absent align="column" reason="No certificate on file" />
                  )}
                </td>
                <td className={cell}>
                  {differs && calc ? (
                    <SourcedFigure value={line.difference} unit="usd" kind="calculated" label={`${line.label}, recalculated less certificate`} source={calc} scale={1000} unitMark={false} align="column" weight="medium" />
                  ) : (
                    <Absent align="column" reason={line.status === 'match' ? 'No difference' : 'Not on the certificate'} />
                  )}
                </td>
                <td className={cx('px-3 py-1.5 text-left', !last && !total && 'border-b border-hairline', strong && 'border-t border-t-ink', total && 'border-b-[3px] border-double border-b-ink')}>
                  {line.status === 'match' ? <StatusDot tone="pass">Agrees</StatusDot> : differs ? <StatusDot tone="attention" emphasis>Differs</StatusDot> : <span className="text-ink-500">Not compared</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {review.availability_fact ? (
        <p className="border-t border-hairline-strong px-4 py-2.5 text-body text-ink-700">
          Availability is stored as a fact and feeds the signals: <FactFigure fact={review.availability_fact} weight="semibold" />
        </p>
      ) : null}
    </Card>
  );
}

export function BorrowingBase() {
  const borrower = useCurrentBorrower();
  const reviews = useBorrowingBase(borrower.id);
  const search = useSearch({ from: '/borrowers/$code/borrowing-base' });
  const navigate = useNavigate({ from: '/borrowers/$code/borrowing-base' });
  return (
    <Load query={reviews} what="The borrowing base reviews" rows={10}>
      {(rows) => {
        if (rows.length === 0) {
          return (
            <div data-ready>
              <EmptyCard
                title="No borrowing base review"
                description="This borrower’s line of credit has no borrowing base, or no certificate has been reviewed yet. Borrowers with a borrowing base have a review for each certificate received."
                action={
                  <Link to="/borrowers/$code/loans" params={{ code: borrower.code }} className="link text-body font-medium">
                    Open the loans
                  </Link>
                }
              />
            </div>
          );
        }
        const selected = rows.find((row) => row.id === search.review) ?? rows[0];
        if (!selected) return null;
        return (
          <div data-ready className="space-y-3">
            <SectionHead
              title="Borrowing base"
              note={`${rows.length} reviews on file · USD thousands · a difference is recalculated less certificate`}
              actions={
                <>
                  <ProvenanceLegend kinds={['calculated', 'extracted']} />
                  <Select
                    label="Review"
                    hideLabel
                    size="sm"
                    className="w-64"
                    value={selected.id}
                    onValueChange={(value) => void navigate({ search: { review: value }, replace: true, resetScroll: false })}
                    options={rows.map((row) => ({ value: row.id, label: `${formatDate(row.period_end)} · ${SHORT[row.outcome]}` }))}
                  />
                </>
              }
            />
            <div className={cx('grid items-start gap-5', selected.work_item && 'xl:grid-cols-[minmax(0,1fr)_400px]')}>
              <ReviewCard key={selected.id} review={selected} code={borrower.code} />
              {selected.work_item ? (
                <aside aria-label="Exception raised on this review" className="xl:sticky xl:top-[68px] xl:max-h-[calc(100vh-88px)] xl:overflow-y-auto xl:rounded-md">
                  <WorkItemPanel key={selected.work_item.id} itemId={selected.work_item.id} />
                </aside>
              ) : null}
            </div>
          </div>
        );
      }}
    </Load>
  );
}
