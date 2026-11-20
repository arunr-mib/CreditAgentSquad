// frontend/src/squad/thread/Time.tsx
const sameDay = (a: Date, b: Date) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/** The time for today; the date and the time for any other day ("18 Nov, 2:02 PM"), with the year when it is not this year. */
export function Time({ ts }: { ts: string }) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const text = sameDay(d, now)
    ? time
    : `${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', ...(d.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }) })}, ${time}`;
  return <time className="sq-faint sq-time" dateTime={ts} title={d.toLocaleString()}>{text}</time>;
}
