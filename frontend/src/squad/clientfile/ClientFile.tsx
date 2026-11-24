// frontend/src/squad/clientfile/ClientFile.tsx
import { ClientOwner } from '../shell/ClientOwner';
import { Link, useParams } from '@tanstack/react-router';
import { useBorrowerByCode } from '@/api/hooks';
import { clientFile, threadHref, type ClientFileView } from '../links';
import { Packages } from './Packages';
import { Runs } from './Runs';
import { Covenants, Documents, Funding, History, Loans, Overview, Reviews, Spreads } from './views';

const VIEWS: Array<[ClientFileView, string]> = [
  ['overview', 'Overview'], ['spreads', 'Spreads'], ['covenants', 'Covenants'], ['documents', 'Documents'],
  ['funding', 'Funding'], ['loans', 'Loans and terms'], ['reviews', 'Reviews'], ['packages', 'Packages'], ['runs', 'Agent runs'], ['history', 'History'],
];
const BODY = { overview: Overview, spreads: Spreads, covenants: Covenants, documents: Documents, funding: Funding, loans: Loans, reviews: Reviews, packages: Packages, runs: Runs, history: History };

/** The client file: the detail behind a thread. Every figure opens its source in the evidence drawer, which pushes the file aside. */
export function ClientFile() {
  const { code, view = 'overview' } = useParams({ strict: false }) as { code: string; view?: string };
  const { borrower, notFound, error, refetch } = useBorrowerByCode(code);
  if (notFound)
    return (
      <div role="alert" className="sq-card">
        <p>There is no client with that code.</p>
        <Link to="/" className="sq-link">Back to Squad</Link>
      </div>
    );
  if (!borrower && error)
    return (
      <div role="alert" className="sq-card">
        <p>The client list could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void refetch()}>Try again</button>
      </div>
    );
  if (!borrower) return <p role="status" className="sq-muted">Opening the client file.</p>;
  const current = VIEWS.find(([id]) => id === view)?.[0];
  const Body = current ? BODY[current] : null;
  return (
    <div className="sq-file" data-ready="">
      <header className="sq-threadhead">
        <div>
          <h1 className="sq-h1">{borrower.name}</h1>
          <p className="sq-faint">Client file · <span className="sq-mono">{borrower.code}</span></p>
          <ClientOwner analyst={borrower.analyst} lookOnly={borrower.look_only} />
        </div>
        <Link {...threadHref(borrower.code)} className="sq-link">Back to the thread</Link>
      </header>
      <nav aria-label="Client file" className="sq-tabs">
        {VIEWS.map(([id, label]) => (
          // exact: the overview's path is a prefix of every other view's, and an active Link marks itself current
          <Link key={id} to={clientFile(borrower.code, id)} activeOptions={{ exact: true }} className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>
        ))}
      </nav>
      {Body ? <Body borrower={borrower} /> : (
        <p role="alert">There is no such part of the client file. <Link to={clientFile(borrower.code)} className="sq-link">Open the overview</Link></p>
      )}
    </div>
  );
}
