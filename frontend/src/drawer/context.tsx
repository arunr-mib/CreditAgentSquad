import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

export type DrawerTab = 'item' | 'copilot';

/** What the Copilot is asked about. The server injects the scope; the model does not choose it. */
export type CopilotScope = { kind: 'portfolio' } | { kind: 'borrower'; code: string } | { kind: 'item'; itemId: string };

/** Text a person asked to carry from a Copilot answer into a decision's reason, with the run it came from. */
export interface ReasonDraft {
  itemId: string;
  text: string;
  /** Changes on every copy, so the form can tell a new draft from one it has already taken. */
  stamp: number;
}

export interface WorkspaceDrawerValue {
  open: boolean;
  tab: DrawerTab;
  itemId: string | null;
  copilotScope: CopilotScope;
  reasonDraft: ReasonDraft | null;
  /** Show an exception with its evidence and decision. */
  openItem: (itemId: string) => void;
  /** Show the Copilot, optionally scoped. */
  openCopilot: (scope?: CopilotScope) => void;
  setTab: (tab: DrawerTab) => void;
  setCopilotScope: (scope: CopilotScope) => void;
  /** Put text into the reason field of an item's decision form, and show that form. */
  draftReason: (itemId: string, text: string) => void;
  close: () => void;
}

const noop = () => {};
const closed: WorkspaceDrawerValue = {
  open: false,
  tab: 'item',
  itemId: null,
  copilotScope: { kind: 'portfolio' },
  reasonDraft: null,
  openItem: noop,
  openCopilot: noop,
  setTab: noop,
  setCopilotScope: noop,
  draftReason: noop,
  close: noop,
};

export const WorkspaceDrawerContext = createContext<WorkspaceDrawerValue>(closed);

/** One drawer for the whole workspace: the selected exception and the Copilot share it. */
export function WorkspaceDrawerProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<DrawerTab>('item');
  const [itemId, setItemId] = useState<string | null>(null);
  const [copilotScope, setCopilotScope] = useState<CopilotScope>({ kind: 'portfolio' });
  const [reasonDraft, setReasonDraft] = useState<ReasonDraft | null>(null);

  const openItem = useCallback((id: string) => {
    setItemId(id);
    setTab('item');
    setOpen(true);
  }, []);
  const openCopilot = useCallback((scope?: CopilotScope) => {
    if (scope) setCopilotScope(scope);
    setTab('copilot');
    setOpen(true);
  }, []);
  const draftReason = useCallback((id: string, text: string) => {
    setReasonDraft({ itemId: id, text, stamp: Date.now() });
    setItemId(id);
    setTab('item');
    setOpen(true);
  }, []);
  const close = useCallback(() => setOpen(false), []);

  const value = useMemo<WorkspaceDrawerValue>(
    () => ({ open, tab, itemId, copilotScope, reasonDraft, openItem, openCopilot, setTab, setCopilotScope, draftReason, close }),
    [open, tab, itemId, copilotScope, reasonDraft, openItem, openCopilot, draftReason, close],
  );
  return <WorkspaceDrawerContext.Provider value={value}>{children}</WorkspaceDrawerContext.Provider>;
}

export function useWorkspaceDrawer(): WorkspaceDrawerValue {
  return useContext(WorkspaceDrawerContext);
}
