// frontend/src/squad/thread/Trail.tsx
import { useState } from 'react';
import { useTrail } from '../api/hooks';

/** "How I got here": which specialist did what, in plain words, loaded only when asked for. */
export function Trail({ workItemId }: { workItemId: string }) {
  const [open, setOpen] = useState(false);
  const trail = useTrail(workItemId, open);
  return (
    <div className="sq-trail">
      <button type="button" className="sq-link" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        How I got here
      </button>
      {open ? (
        trail.data ? (
          trail.data.steps.length === 0 ? (
            <p className="sq-muted">No agent work is recorded behind this case.</p>
          ) : (
            <ol className="sq-steps">
              {trail.data.steps.map((s) => (
                <li key={s.n}>
                  <b>{s.who}</b> <small className="sq-faint">{s.role_line}</small>
                  <span>{s.text}</span>
                  <span className="sq-check">✓ {s.check}</span>
                </li>
              ))}
            </ol>
          )
        ) : (
          <p role="status" className="sq-muted">Loading the trail.</p>
        )
      ) : null}
    </div>
  );
}
