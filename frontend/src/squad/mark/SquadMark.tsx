// frontend/src/squad/mark/SquadMark.tsx
export type MarkState = 'rest' | 'working' | 'needs' | 'responding';

const DOTS: Array<[number, number]> = [[50, 18], [82, 50], [50, 82], [18, 50]];

/**
 * Four specialist dots around one core (lavender: dots #8F7BF0, core #4A35B8), the same at every size.
 * Needs you adds an ember ring round the core, never a separate shape. Decorative: the words beside it carry the meaning.
 */
export function SquadMark({ size = 28, state = 'rest', label, pulseKey = 0 }: { size?: number; state?: MarkState; label?: string; pulseKey?: number }) {
  const working = state === 'working';
  const needs = state === 'needs';
  const responding = state === 'responding';
  const a11y = label ? ({ role: 'img', 'aria-label': label } as const) : ({ 'aria-hidden': true } as const);
  return (
    <svg className={`sq-mk sq-mk-${state}`} width={size} height={size} viewBox="0 0 100 100" data-state={state} {...a11y}>
      {state === 'responding' ? <circle key={`r${pulseKey}`} className="sq-ripple" cx="50" cy="50" r="30" fill="none" stroke="#8f7bf0" strokeWidth="3" /> : null}
      <g key={`o${pulseKey}`} className={working || responding ? 'sq-orbit' : undefined} fill="#8f7bf0">
        {DOTS.map(([x, y], i) => (
          <circle key={i} className="sq-dot" cx={x} cy={y} r={working && i % 2 ? 8 : 11} opacity={working && i % 2 ? 0.7 : 1} />
        ))}
      </g>
      <circle
        className={working ? 'sq-core sq-core-breathe' : 'sq-core'}
        cx="50"
        cy="50"
        r={needs ? 15 : 17}
        fill="#4a35b8"
        {...(needs ? { stroke: 'var(--sq-ember)', strokeWidth: size < 24 ? 7 : 5.5 } : {})}
      />
    </svg>
  );
}
