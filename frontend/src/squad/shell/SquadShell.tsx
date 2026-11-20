// frontend/src/squad/shell/SquadShell.tsx
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { useCallback, useState } from 'react';
import { CommandPalette, useCommandPaletteShortcut } from '@/design';
import { useAuth } from '@/auth/context';
import { useBorrowers } from '@/api/hooks';
import { useBriefing } from '../api/hooks';
import { LookProvider, useLook } from '../useLook';
import { PresenceLine, PresenceProvider } from '../presence/Presence';
import { buildCommands } from './commands';
import { SquadNav } from './SquadNav';

const NAV_KEY = 'squad.nav.collapsed';
function storedCollapsed(): boolean {
  try {
    return localStorage.getItem(NAV_KEY) !== 'false'; // collapsed unless the person opened it
  } catch {
    return true;
  }
}

function Frame() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const briefing = useBriefing();
  const borrowers = useBorrowers();
  const { setLook } = useLook();
  const [collapsed, setCollapsed] = useState(storedCollapsed);
  const [paletteOpen, setPaletteOpen] = useState(false);
  useCommandPaletteShortcut(useCallback(() => setPaletteOpen((o) => !o), []));
  const toggle = () =>
    setCollapsed((c) => {
      try {
        localStorage.setItem(NAV_KEY, String(!c));
      } catch {
        /* not remembered */
      }
      return !c;
    });
  const commands = buildCommands({
    clients: (borrowers.data ?? []).map((b) => ({ code: b.code, name: b.name })),
    go: (path) => void navigate({ to: path }),
    setLook,
    role: user?.role ?? '',
  });
  const needs = briefing.data?.needs_you ?? 0;
  return (
    <PresenceProvider needs={needs}>
      <div className="sq-shell" data-collapsed={collapsed}>
        <a href="#main" className="sq-skip">Skip to content</a>
        <SquadNav collapsed={collapsed} onToggle={toggle} needs={needs} openClients={briefing.data?.open_clients ?? []}
          pathname={pathname} userName={user?.name ?? ''} role={user?.role ?? ''} onSignOut={() => void signOut()} />
        <div className="sq-stage">
          <main id="main" tabIndex={-1} className="sq-main">
            <PresenceLine />
            <Outlet />
          </main>
        </div>
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
