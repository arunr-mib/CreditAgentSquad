// frontend/src/squad/thread/Trail.tsx
import { useState } from 'react';
import { AgentBody } from '@/source/AgentBody';
import { useTrail } from '../api/hooks';
import type { Trail as TrailData } from '../api/types';

const FAILED = /fail|error|abstain|refus|reject/i;
const show = (value: unknown) => (typeof value === 'string' ? value : JSON.stringify(value));

function Calculation({ calc }: { calc: NonNullable<TrailData['calculation']> }) {
  const outputs = Object.entries(calc.outputs ?? {});
  return (
    <div role="group" aria-label="Calculation" className="sq-calc">
      <b className="sq-ident">{calc.formula_key}</b>
      {calc.inputs.length > 0 ? (
        <ul className="sq-steps" aria-label="Inputs">
          {calc.inputs.map((input, i) => (
            <li key={`${input.fact_id ?? input.key ?? i}`}>
              <span>{input.name ?? input.key ?? 'Input'}: </span>
              {/* A stored fact shows as its figure with its source; only a stored value without a fact id is printed as stored. */}
              {input.fact_id ? <AgentBody text={`{{fact:${input.fact_id}}}`} /> : <span>{show(input.value ?? '')}</span>}
            </li>
          ))}
        </ul>
      ) : null}
      {outputs.length > 0 ? (
        <ul className="sq-steps" aria-label="Outputs">
          {outputs.map(([key, value]) => <li key={key}><span>{key.replace(/_/g, ' ')}: {show(value)}</span></li>)}
        </ul>
      ) : null}
    </div>
  );
}

/** "How I got here": which specialist did what, the calculation and the checks, in plain words, loaded only when asked for. */
export function Trail({ workItemId }: { workItemId: string }) {
  const [open, setOpen] = useState(false);
  const trail = useTrail(workItemId, open);
  const data = trail.data;
  return (
    <div className="sq-trail" id={`trail-${workItemId}`}>
      <button type="button" className="sq-link" aria-expanded={open} aria-controls={`trail-${workItemId}`} onClick={() => setOpen((o) => !o)}>
        How I got here
      </button>
      {open ? (
        trail.error ? (
          <p role="alert" className="sq-muted">
            The trail could not be loaded. <button type="button" className="sq-link" onClick={() => void trail.refetch()}>Try again</button>
          </p>
        ) : data ? (
          data.steps.length === 0 && !data.calculation && data.checks.length === 0 ? (
            <p className="sq-muted">Nothing to show: no agent ran on this case. It was raised by code, or loaded with the book, so there are no agent steps or checks behind it.</p>
          ) : (
            <>
              <ol className="sq-steps">
                {data.steps.map((s) => (
                  <li key={s.n}>
                    <b>{s.who}</b> <small className="sq-faint">{s.role_line}</small>
                    <span>{s.text}</span>
                    <span className={FAILED.test(s.check) ? 'sq-check sq-check-bad' : 'sq-check'}>{FAILED.test(s.check) ? '✗' : '✓'} {s.check}</span>
                  </li>
                ))}
              </ol>
              {data.calculation ? <Calculation calc={data.calculation} /> : null}
              {data.checks.length > 0 ? (
                <ul className="sq-steps" aria-label="Checks that ran">
                  {data.checks.map((c, i) => (
                    <li key={i}>
                      <span><b>{c.layer ?? 'check'}</b> {c.check ?? ''}{c.action ? ` · ${c.action}` : ''}</span>
                      {c.detail ? <span className="sq-faint">{c.detail}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          )
        ) : (
          <p role="status" className="sq-muted">Loading the trail.</p>
        )
      ) : null}
    </div>
  );
}
