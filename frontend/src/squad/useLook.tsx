// frontend/src/squad/useLook.tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from '@/auth/context';
import { applyLook, defaultLookFor, LOOK_IDS, type LookId } from './looks';

interface LookValue {
  look: LookId;
  setLook: (id: LookId) => void;
}
const LookContext = createContext<LookValue>({ look: 'night', setLook: () => {} });
export const useLook = () => useContext(LookContext);

const storageKey = (userId: string) => `squad.look.${userId}`;

function remembered(userId: string | undefined): LookId | null {
  if (!userId) return null;
  try {
    const value = localStorage.getItem(storageKey(userId));
    return LOOK_IDS.includes(value as LookId) ? (value as LookId) : null;
  } catch {
    return null;
  }
}

export function LookProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const initial = remembered(user?.id) ?? defaultLookFor(user?.role ?? '');
  const [look, setLookState] = useState<LookId>(initial);
  useEffect(() => applyLook(look), [look]);
  const setLook = useCallback(
    (id: LookId) => {
      setLookState(id);
      try {
        if (user) localStorage.setItem(storageKey(user.id), id);
      } catch {
        /* a blocked store only means the choice is not remembered */
      }
    },
    [user],
  );
  const value = useMemo(() => ({ look, setLook }), [look, setLook]);
  return <LookContext.Provider value={value}>{children}</LookContext.Provider>;
}
