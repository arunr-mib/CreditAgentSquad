// frontend/src/squad/presence/Presence.tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { SquadMark, type MarkState } from '../mark/SquadMark';

interface PresenceApi {
  state: MarkState;
  said: string;
  say: (text: string, ms?: number) => void;
  beginWork: () => () => void;
  pulse: () => void;
  pulseKey: number;
}
const PresenceContext = createContext<PresenceApi>({ state: 'rest', said: '', say: () => {}, beginWork: () => () => {}, pulse: () => {}, pulseKey: 0 });
export const usePresence = () => useContext(PresenceContext);

const SAY_MS = 6000;
const PULSE_MS = 900;

export function PresenceProvider({ needs, children }: { needs: number; children: ReactNode }) {
  const [busy, setBusy] = useState(0);
  const [responding, setResponding] = useState(false);
  const [pulseKey, setPulseKey] = useState(0);
  const [said, setSaid] = useState('');
  const sayTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const pulseTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => {
    clearTimeout(sayTimer.current);
    clearTimeout(pulseTimer.current);
  }, []);

  const say = useCallback((text: string, ms = SAY_MS) => {
    clearTimeout(sayTimer.current);
    setSaid(text);
    sayTimer.current = setTimeout(() => setSaid(''), ms);
  }, []);
  const beginWork = useCallback(() => {
    setBusy((n) => n + 1);
    let ended = false;
    return () => {
      if (!ended) {
        ended = true;
        setBusy((n) => Math.max(0, n - 1));
      }
    };
  }, []);
  const pulse = useCallback(() => {
    clearTimeout(pulseTimer.current);
    setResponding(true);
    setPulseKey((k) => k + 1);
    pulseTimer.current = setTimeout(() => setResponding(false), PULSE_MS);
  }, []);

  const state: MarkState = busy > 0 ? 'working' : responding ? 'responding' : needs > 0 ? 'needs' : 'rest';
  const value = useMemo(() => ({ state, said, say, beginWork, pulse, pulseKey }), [state, said, say, beginWork, pulse, pulseKey]);
  return <PresenceContext.Provider value={value}>{children}</PresenceContext.Provider>;
}

const WORDS: Record<MarkState, string> = { rest: 'watching your clients', working: 'working', needs: 'needs you', responding: 'answering' };

/** Centred above the conversation. The status line is reserved, so a confirmation never moves or covers content. */
export function PresenceLine() {
  const { state, said, pulseKey } = usePresence();
  return (
    <div className="sq-presence">
      <div className="sq-presence-id" title={`Credit Squad · ${WORDS[state]}`}>
        <SquadMark size={42} state={state} pulseKey={pulseKey} />
        <b>Credit Squad</b>
        <span className="sq-sr" aria-live="polite">: {WORDS[state]}</span>
      </div>
      <div className="sq-say" role="status" aria-live="polite">
        {said}
      </div>
    </div>
  );
}
