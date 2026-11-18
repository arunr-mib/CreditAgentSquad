import { Link } from '@tanstack/react-router';
import { ChevronDown, Clock } from 'lucide-react';
import { useAuth } from '@/auth/context';
import { formatDate, Popover } from '@/design';
import { cx } from '@/lib/cx';
import { STALE_AFTER_DAYS, useAsOf } from './AsOf';

/** The date the workspace is read at: a compact control that opens what the simulated clock is and how fresh the data is. */
export function AsOfControl() {
  const { asOf, latestDocument, daysSinceLatestDocument } = useAsOf();
  const { can } = useAuth();
  const stale = daysSinceLatestDocument !== null && daysSinceLatestDocument > STALE_AFTER_DAYS;
  return (
    <Popover
      label="Simulated clock"
      align="end"
      className="w-[320px] p-4"
      trigger={
        <button
          type="button"
          className="inline-flex h-8 shrink-0 items-center gap-2 rounded-sm border border-hairline-strong bg-surface px-2.5 text-body text-ink t-colors hover:border-ink-400 data-[state=open]:border-ink-400"
        >
          <Clock size={14} strokeWidth={1.75} aria-hidden className="shrink-0 text-ink-500 @max-[400px]:hidden" />
          <span className="whitespace-nowrap text-ink-500 @max-[520px]:sr-only">As of</span>
          <span data-as-of className="tnum font-medium whitespace-nowrap">
            {asOf ? formatDate(asOf) : 'reading the clock'}
          </span>
          <span className="sr-only">, simulated clock</span>
          {stale ? (
            // The same words at every width; where the bar is short only the count of days is drawn, and the popover says the rest.
            <span data-stale className="inline-flex items-center gap-1 text-caption font-medium whitespace-nowrap text-amber">
              <span aria-hidden className="size-[7px] shrink-0 rounded-full bg-amber-mark" />
              <span className="sr-only">Data may be out of date: </span>
              <span className="@max-[1100px]:sr-only">no document for </span>
              {daysSinceLatestDocument} days
            </span>
          ) : null}
          <ChevronDown size={13} aria-hidden className="shrink-0 text-ink-500 @max-[520px]:hidden" />
        </button>
      }
    >
      <p className="eyebrow">Simulated clock</p>
      <p className="tnum mt-1 text-heading font-semibold text-ink">{asOf ? formatDate(asOf) : 'Not read yet'}</p>
      <p className="mt-1 text-body text-pretty text-ink-700">
        The demonstration runs on a clock that a person sets. Due dates, overdue items and cycle stages follow this date, not today’s.
      </p>
      <p className="eyebrow mt-3">How fresh the data is</p>
      <p data-freshness className={cx('mt-1 text-body text-pretty', stale ? 'font-medium text-amber' : 'text-ink-700')}>
        {latestDocument && daysSinceLatestDocument !== null
          ? `The newest document on file was received ${formatDate(latestDocument)}, ${daysSinceLatestDocument === 0 ? 'the same day as' : `${daysSinceLatestDocument} ${daysSinceLatestDocument === 1 ? 'day' : 'days'} before`} this date.${stale ? ` Nothing has arrived for more than ${STALE_AFTER_DAYS} days, so figures may be out of date.` : ''}`
          : 'No document has been received on or before this date.'}
      </p>
      <p className="mt-2 text-body text-ink-700">
        {can('advance_clock') ? (
          <Link to="/governance" search={{ tab: 'clock' }} className="link font-medium">
            Set the date under Governance
          </Link>
        ) : (
          'An administrator sets the date under Governance.'
        )}
      </p>
    </Popover>
  );
}
