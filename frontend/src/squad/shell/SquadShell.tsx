// frontend/src/squad/shell/SquadShell.tsx
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { useCallback, useState } from 'react';
import { CommandPalette, useCommandPaletteShortcut } from '@/design';
import { useAuth } from '@/auth/context';
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
import { surfaceOf } from './surface';

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
  const showApprovals = briefing.data?.approvals.offered ?? false;
  const oversight = briefing.data?.oversight?.offered ?? false;
  const commands = buildCommands({
    clients: (borrowers.data ?? []).map((b) => ({ code: b.code, name: b.name })),
    go: (path) => void navigate({ to: path }),
    setLook,
    oversight,
    approvals: showApprovals,
  });
  const needs = briefing.data?.needs_you ?? 0;
  const surface = surfaceOf(pathname);
  return (
    <PresenceProvider needs={needs}>
      <div className="sq-shell" data-collapsed={navCollapsed}>
        <a href="#main" className="sq-skip">Skip to content</a>
        <SquadNav collapsed={navCollapsed} onToggle={toggle} needs={needs} showApprovals={showApprovals} openClients={briefing.data?.open_clients ?? []}
          pathname={pathname} userName={user?.name ?? ''} oversight={oversight} onSignOut={() => void signOut()} />
        <div className="sq-stage">
          <main id="main" tabIndex={-1} className="sq-main" data-surface={surface}>
            <PresenceLine />
            <Outlet />
          </main>
        </div>
        <EvidenceResizer navWidth={navCollapsed ? 64 : 248} />
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
