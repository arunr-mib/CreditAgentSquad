import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from '@/auth/context';
import { applyLook, clearLook, defaultLookFor, LOOK_IDS, type LookId } from './looks';

interface LookValue {
  look: LookId;
  setLook: (id: LookId) => void;
  /** The Squad root element, so portalled menus stay inside the look's variables. */
  root: HTMLElement | null;
}
const LookContext = createContext<LookValue>({ look: 'night', setLook: () => {}, root: null });
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
  const userId = user?.id;
  const role = user?.role ?? '';
  const [root, setRoot] = useState<HTMLElement | null>(null);
  // A choice made in this session belongs to the person who made it; anyone else re-resolves from storage, then role.
  const [picked, setPicked] = useState<{ userId: string | undefined; id: LookId } | null>(null);
  const resolved = useMemo(() => remembered(userId) ?? defaultLookFor(role), [userId, role]);
  const look = picked && picked.userId === userId ? picked.id : resolved;

  useEffect(() => {
    if (!root) return;
    applyLook(look, root);
    return () => clearLook(root);
  }, [look, root]);

  const setLook = useCallback(
    (id: LookId) => {
      setPicked({ userId, id });
      try {
        if (userId) localStorage.setItem(storageKey(userId), id);
      } catch {
        /* a blocked store only means the choice is not remembered */
      }
    },
    [userId],
  );
  const value = useMemo(() => ({ look, setLook, root }), [look, setLook, root]);
  return (
    <LookContext.Provider value={value}>
      <div className="sq-root" ref={setRoot}>
        {children}
      </div>
    </LookContext.Provider>
  );
}
