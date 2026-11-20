// frontend/src/squad/shell/SquadShell.tsx
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { CommandPalette, useCommandPaletteShortcut } from '@/design';
import { useAuth } from '@/auth/context';
import { defaultCopilotScope, useWorkspaceDrawer } from '@/drawer/context';
import { WorkspaceDrawer } from '@/drawer/WorkspaceDrawer';
import { useBorrowers } from '@/api/hooks';
import { useSource } from '@/source/context';
import { useBriefing } from '../api/hooks';
import { useLedgerHeartbeat } from '../api/polling';
import { LookProvider, useLook } from '../useLook';
import { EvidenceResizer } from '../evidence/EvidenceResizer';
import { PresenceLine, PresenceProvider } from '../presence/Presence';
import { useNavCollapse } from './useNavCollapse';
import { buildCommands } from './commands';
import { SquadNav } from './SquadNav';

function Frame() {
  const { user, signOut } = useAuth();
  useLedgerHeartbeat({ enabled: Boolean(user) });
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const briefing = useBriefing();
  const borrowers = useBorrowers();
  const { setLook } = useLook();
  const { current: evidence } = useSource();
  const { collapsed: navCollapsed, toggle } = useNavCollapse(evidence !== null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  useCommandPaletteShortcut(useCallback(() => setPaletteOpen((o) => !o), []));
  const { open: drawerOpen, tab: drawerTab, itemId: drawerItem, borrowerCode: drawerBorrower, openCopilot, close: closeDrawer } = useWorkspaceDrawer();
  // Ctrl or Cmd + J: the Copilot, as in the legacy shell, so the legacy screens' drawer keeps working.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'j') return;
      event.preventDefault();
      if (drawerOpen && drawerTab === 'copilot') closeDrawer();
      else openCopilot(defaultCopilotScope({ open: drawerOpen, itemId: drawerItem, borrowerCode: drawerBorrower }, pathname));
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen, drawerTab, drawerItem, drawerBorrower, openCopilot, closeDrawer, pathname]);
  const commands = buildCommands({
    clients: (borrowers.data ?? []).map((b) => ({ code: b.code, name: b.name })),
    go: (path) => void navigate({ to: path }),
    setLook,
    role: user?.role ?? '',
  });
  const needs = briefing.data?.needs_you ?? 0;
  return (
    <PresenceProvider needs={needs}>
      <div className="sq-shell" data-collapsed={navCollapsed}>
        <a href="#main" className="sq-skip">Skip to content</a>
        <SquadNav collapsed={navCollapsed} onToggle={toggle} needs={needs} openClients={briefing.data?.open_clients ?? []}
          pathname={pathname} userName={user?.name ?? ''} role={user?.role ?? ''} onSignOut={() => void signOut()} />
        <div className="sq-stage">
          <main id="main" tabIndex={-1} className="sq-main">
            <PresenceLine />
            <Outlet />
          </main>
        </div>
        <EvidenceResizer navWidth={navCollapsed ? 64 : 248} />
        <WorkspaceDrawer />
        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} placeholder="Search clients and commands" />
      </div>
    </PresenceProvider>
  );
}

export function SquadShell() {
  return (
    <LookProvider>
      <Frame />
    </LookProvider>
  );
}
