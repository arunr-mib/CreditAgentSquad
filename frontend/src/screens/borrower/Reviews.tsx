import { Link } from '@tanstack/react-router';
import { useActions, useReviewSheets } from '@/api/hooks';
import { Button, Card, CardHeader, formatDate, StatusDot } from '@/design';
import { humanize, quarterLabel } from '@/domain/labels';
import { EmptyCard, Load, Notice } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';

export function Reviews() {
  const borrower = useCurrentBorrower();
  const sheets = useReviewSheets({ borrower_id: borrower.id });
  const actions = useActions({ status: 'all', borrower_id: borrower.id });
  return (
    <div data-ready={sheets.data ? '' : undefined} className="grid items-start gap-5 xl:grid-cols-2">
      <Card>
        <CardHeader as="h2" title="Review sheets" meta="One per monitoring cycle, assembled by code from stored facts" />
        <Load query={sheets} what="The review sheets" rows={3}>
          {(rows) =>
            rows.length === 0 ? (
              <p className="border-t border-hairline px-4 py-3 text-body text-pretty text-ink-700">
                No review sheet has been prepared. A sheet is built when the cycle reaches review preparation and the Review Agent has drafted commentary for a person to approve.
              </p>
            ) : (
              <ul className="border-t border-ink">
                {rows.map((sheet) => (
                  <li key={sheet.id} className="border-b border-hairline last:border-b-0">
                    <Link to="/review-room" search={{ sheet: sheet.id }} className="flex min-h-[34px] items-center justify-between gap-4 px-4 py-1.5 text-body t-colors hover:bg-hover last:rounded-b-md">
                      <span className="font-medium text-ink">{quarterLabel(sheet.period_end)}</span>
                      <StatusDot tone={sheet.status === 'reviewed' || sheet.status === 'released' ? 'pass' : 'attention'}>{sheet.status === 'draft' ? 'Draft, not yet approved' : humanize(sheet.status)}</StatusDot>
                    </Link>
                  </li>
                ))}
              </ul>
            )
          }
        </Load>
      </Card>
      <Card>
        <CardHeader
          as="h2"
          title="Actions"
          meta="Raised in review, each with an owner and a due date"
          actions={
            <Button asChild size="sm">
              <Link to="/review-room">Open the review room</Link>
            </Button>
          }
        />
        <Load query={actions} what="The actions" rows={3}>
          {(rows) =>
            rows.length === 0 ? (
              <p className="border-t border-hairline px-4 py-3 text-body text-ink-700">No action has been raised for this borrower.</p>
            ) : (
              <ul className="border-t border-ink">
                {rows.map((action) => (
                  <li key={action.id} className="grid min-h-[34px] grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-x-4 border-b border-hairline px-4 py-1.5 text-body last:border-b-0">
                    <span className="font-medium text-ink">{action.title}</span>
                    <span className="text-ink-700">{action.owner_name ?? 'No owner'}</span>
                    <StatusDot tone={action.overdue ? 'attention' : action.status === 'done' ? 'pass' : 'neutral'}>
                      {action.status === 'done' ? 'Done' : action.due_date ? `${action.overdue ? 'Overdue, ' : 'Due '}${formatDate(action.due_date)}` : humanize(action.status)}
                    </StatusDot>
                  </li>
                ))}
              </ul>
            )
          }
        </Load>
      </Card>
    </div>
  );
}

/** Placeholder: the publishing routes are still being written. This tab calls nothing. */
export function Packages() {
  const borrower = useCurrentBorrower();
  return (
    <div data-ready className="space-y-4">
      <Notice title="Packages are not built yet">
        Publishing to Word, Excel and PowerPoint, and the snapshot that freezes every fact behind a released package, arrive with the publishing milestone. This tab is a placeholder: it
        requests nothing and shows no data.
      </Notice>
      <EmptyCard
        title={`No package for ${borrower.name}`}
        description="When publishing is built, a released package will list its files here, each figure in them carrying the id of the fact it came from."
      />
    </div>
  );
}
