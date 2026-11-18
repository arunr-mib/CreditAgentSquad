import { Link } from '@tanstack/react-router';
import { useBorrowers } from '@/api/hooks';

/** A borrower at a glance, in the workspace drawer. */
export function BorrowerTearSheet({ code }: { code: string }) {
  const borrowers = useBorrowers();
  const borrower = borrowers.data?.find((row) => row.code === code);
  return (
    <div data-tear-sheet={code} className="px-4 py-4">
      <p className="eyebrow">Borrower</p>
      <h2 className="mt-0.5 text-heading font-semibold text-ink">{borrower?.name ?? code}</h2>
      <Link to="/borrowers/$code" params={{ code }} className="link mt-3 inline-block text-body font-medium">
        Open the borrower page
      </Link>
    </div>
  );
}
