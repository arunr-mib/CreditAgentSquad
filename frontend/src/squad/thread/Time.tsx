// frontend/src/squad/thread/Time.tsx
export function Time({ ts }: { ts: string }) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return null;
  return <time className="sq-faint sq-time" dateTime={ts} title={d.toLocaleString()}>{d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</time>;
}
