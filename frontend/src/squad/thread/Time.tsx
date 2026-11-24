// frontend/src/squad/thread/Time.tsx
const sameDay = (a: Date, b: Date) => a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth() && a.getUTCDate() === b.getUTCDate();
const two = (n: number) => String(n).padStart(2, '0');

/** When something was recorded, in UTC and saying so, as the client file and the ledger show it: one convention for
 * everyone, wherever they sit. The time for today ("14:02 UTC"); the date and the time for any other day
 * ("18 Nov, 14:02 UTC"), with the year when it is not this year. */
export function Time({ ts }: { ts: string }) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  const time = `${two(d.getUTCHours())}:${two(d.getUTCMinutes())} UTC`;
  const text = sameDay(d, now)
    ? time
    : `${d.toLocaleDateString('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short', ...(d.getUTCFullYear() === now.getUTCFullYear() ? {} : { year: 'numeric' }) })}, ${time}`;
  return <time className="sq-faint sq-time" dateTime={ts} title={`${d.toISOString().slice(0, 16).replace('T', ' ')} UTC`}>{text}</time>;
}
