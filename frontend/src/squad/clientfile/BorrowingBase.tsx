import { useState } from 'react';
import { useBorrowingBase } from '@/api/hooks';
import type { BorrowerRow, BorrowingBaseReview } from '@/api/schema';
import { formatDate } from '@/design';
import { useSource, type SourceRef } from '@/source/context';
import { Absent, FactFigure, SourcedFigure } from '@/source/figures';

const STRONG = new Set(['ar_eligible', 'inventory_eligible', 'borrowing_base', 'borrowing_limit', 'availability', 'over_advance', 'ar_ineligible_total']);

function Review({ review, code }: { review: BorrowingBaseReview & { outcome_label?: string }; code: string }) {
  const source = useSource();
  const calc: SourceRef | null = review.calc_run_id ? { type: 'calculation', id: review.calc_run_id, title: `Borrowing base, ${formatDate(review.period_end)}` } : null;
  const certificate: SourceRef | null = review.certificate_document
    ? { type: 'document', documentId: review.certificate_document.id, page: 1, title: review.certificate_document.title, borrowerCode: code }
    : null;
  const context = `As of ${formatDate(review.period_end)}`;
  return (
    <div>
      <p>
        {review.loan_name ?? 'Line of credit'} · recalculated by code from the aging and inventory detail · <b>{review.outcome_label ?? review.outcome}</b>
        {certificate ? <> · <button type="button" className="sq-link" onClick={() => source.open(certificate)}>The certificate</button></> : null}
      </p>
      <div className="sq-tablewrap">
        <table className="sq-table" aria-label={`Borrowing base as of ${formatDate(review.period_end)}`}>
          <thead><tr><th scope="col">Line</th><th scope="col" className="sq-num">Recalculated</th><th scope="col" className="sq-num">Certificate</th><th scope="col" className="sq-num">Difference</th><th scope="col">Check</th></tr></thead>
          <tbody>
            {review.lines.map((l) => {
              const differs = l.status === 'mismatch';
              const weight = STRONG.has(l.line) ? 'semibold' : 'regular';
              return (
                <tr key={l.line}>
                  <th scope="row" style={{ paddingLeft: 12 + l.depth * 14 }}>{l.label}</th>
                  <td className="sq-num">{calc ? <SourcedFigure value={l.computed} unit="usd" kind="calculated" label={`${l.label}, recalculated`} context={context} source={calc} align="column" weight={weight} /> : <Absent align="column" reason="Not recalculated" />}</td>
                  <td className="sq-num">{certificate ? <SourcedFigure value={l.certificate} unit="usd" kind="extracted" label={`${l.label}, on the certificate`} context={context} source={certificate} align="column" /> : <Absent align="column" reason="No certificate on file" />}</td>
                  <td className="sq-num">{differs && calc ? <SourcedFigure value={l.difference} unit="usd" kind="calculated" label={`${l.label}, recalculated less certificate`} source={calc} align="column" weight="medium" /> : <Absent align="column" reason={l.status === 'match' ? 'No difference' : 'Not on the certificate'} />}</td>
                  <td>{l.status === 'match' ? 'Agrees' : differs ? <span className="sq-tag sq-tag-attention">Differs</span> : <span className="sq-faint">Not compared</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {review.availability_fact ? <p>Availability is stored as a fact and feeds the signals: <FactFigure fact={review.availability_fact} weight="semibold" /></p> : null}
    </div>
  );
}

/** The borrowing base reviews: each line as recalculated beside the certificate, a difference where they differ, earlier reviews by period. */
export function BorrowingBase({ borrower }: { borrower: BorrowerRow }) {
  const reviews = useBorrowingBase(borrower.id);
  const [chosen, setChosen] = useState<string | null>(null);
  if (reviews.isPending) return <p role="status" className="sq-muted">Reading the borrowing base.</p>;
  if (reviews.error || !reviews.data) return <p role="alert">The borrowing base could not be loaded. Try again in a moment.</p>;
  if (reviews.data.length === 0) return <p className="sq-muted">No borrowing base review: this client’s line has no borrowing base, or no certificate has been reviewed yet.</p>;
  const selected = reviews.data.find((r) => r.id === chosen) ?? reviews.data[0]!;
  return (
    <section className="sq-card" aria-label="Borrowing base">
      <h2 className="sq-h2">Borrowing base · {formatDate(selected.period_end)}</h2>
      {reviews.data.length > 1 ? (
        <div className="sq-field">
          <label htmlFor="bb-review">Review</label>
          <select id="bb-review" value={selected.id} onChange={(e) => setChosen(e.target.value)}>
            {reviews.data.map((r) => <option key={r.id} value={r.id}>{formatDate(r.period_end)} · {(r as { outcome_label?: string }).outcome_label ?? r.outcome}</option>)}
          </select>
        </div>
      ) : null}
      <Review key={selected.id} review={selected} code={borrower.code} />
    </section>
  );
}
