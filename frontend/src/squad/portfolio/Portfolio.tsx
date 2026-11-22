import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { usePortfolio } from '../api/hooks';
import { MeasureNow, TrendBars } from '../clientfile/Measure';
import { threadHref } from '../links';

/** Every client by the measure it is watched by, lowest first as the server orders it; a row opens the client's thread. */
export function Portfolio() {
  const portfolio = usePortfolio();
  const [mineOnly, setMineOnly] = useState(false);
  if (portfolio.isPending) return <p role="status" className="sq-muted">Reading the portfolio.</p>;
  if (portfolio.error || !portfolio.data)
    return (
      <div role="alert">
        <p>The portfolio could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void portfolio.refetch()}>Try again</button>
      </div>
    );
  const { sections, owns_clients: owns } = portfolio.data;
  return (
    <div className="sq-portfolio" data-ready="">
      <h1 className="sq-h1">My Portfolio</h1>
      {owns ? <label className="sq-check-label sq-filter"><input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} /> Only my clients</label> : null}
      {sections.map((s) => {
        const rows = s.rows.filter((r) => !(owns && mineOnly) || r.mine);
        return (
          <section key={s.template_id} aria-label={s.title}>
            <h2 className="sq-h2">{s.title}</h2>
            {rows.length === 0 ? <p className="sq-muted">None of these clients is yours.</p> : (
              <div className="sq-tablewrap"><table className="sq-table" aria-label={s.title}>
                <thead><tr><th scope="col">Client</th><th scope="col">Analyst</th><th scope="col" className="sq-num">Open</th><th scope="col" className="sq-num">{s.measure_label}</th><th scope="col">Trend</th></tr></thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.borrower_id} data-borrower={r.code}>
                      <th scope="row"><Link {...threadHref(r.code)} className="sq-link">{r.name}</Link></th>
                      <td>{r.analyst ?? <span className="sq-faint">No analyst</span>}</td>
                      <td className="sq-num">{r.open}</td>
                      <td className="sq-num" data-measure-cell><MeasureNow series={r.measure} /></td>
                      <td><TrendBars points={r.measure.points} label={`${r.name}: ${s.measure_label}`} /></td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
          </section>
        );
      })}
    </div>
  );
}
