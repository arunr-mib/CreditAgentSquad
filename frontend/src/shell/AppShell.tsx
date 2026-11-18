import { Outlet, useRouterState } from '@tanstack/react-router';
import { Search } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { CommandPalette, Kbd, useCommandPaletteShortcut } from '@/design';
import { useWorkspaceDrawer } from '@/drawer/context';
import { WorkspaceDrawer } from '@/drawer/WorkspaceDrawer';
import { cx } from '@/lib/cx';
import { AsOfControl } from './AsOfControl';
import { borrowerCodeIn, useShellCommands } from './commands';
import { Copilot } from './Copilot';
import { Rail } from './Rail';
import { useRail } from './useRail';
import { UserMenu } from './UserMenu';

export function AppShell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const [paletteOpen, setPaletteOpen] = useState(false);
  useCommandPaletteShortcut(useCallback(() => setPaletteOpen((open) => !open), []));
  const { open: drawerOpen, tab: drawerTab, openCopilot, close: closeDrawer } = useWorkspaceDrawer();
  const rail = useRail(drawerOpen);
  const commands = useShellCommands(pathname);
  // Ctrl or Cmd + J: the Copilot, scoped to the borrower on screen when there is one.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'j') return;
      event.preventDefault();
      if (drawerOpen && drawerTab === 'copilot') closeDrawer();
      else {
        const code = borrowerCodeIn(pathname);
        openCopilot(code ? { kind: 'borrower', code } : undefined);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen, drawerTab, openCopilot, closeDrawer, pathname]);

  return (
    <div className="flex min-h-screen bg-canvas">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[70] focus:rounded-sm focus:bg-surface focus:px-3 focus:py-1.5 focus:text-body focus:font-medium focus:text-cobalt"
      >
        Skip to content
      </a>
      <Rail pathname={pathname} rail={rail} />
      <div className="flex min-w-0 flex-1 flex-col">
        {/*
          The bar is a container: what it shows follows its own width, not the window's, because the rail
          beside it has two widths. Under 520 px controls are icons; from 900 px the search has its words.
        */}
        <header className="@container sticky top-0 z-30 flex h-12 shrink-0 items-center justify-between gap-2 border-b border-hairline-strong bg-canvas px-4 sm:gap-4 sm:px-6">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex size-8 shrink-0 items-center justify-center gap-2 rounded-sm border border-hairline-strong bg-surface text-body text-ink-500 t-colors hover:border-ink-400 hover:text-ink-700 @min-[900px]:w-auto @min-[900px]:max-w-[400px] @min-[900px]:min-w-[220px] @min-[900px]:flex-1 @min-[900px]:shrink @min-[900px]:justify-start @min-[900px]:px-2.5 [&>span]:sr-only @min-[900px]:[&>span]:not-sr-only"
            aria-keyshortcuts="Control+K Meta+K"
          >
            <Search size={14} aria-hidden className="shrink-0" />
            <span className="min-w-0 flex-1 overflow-hidden text-left whitespace-nowrap">Search borrowers and commands</span>
            <span aria-hidden>
              <Kbd>Ctrl K</Kbd>
            </span>
          </button>
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <Copilot />
            <AsOfControl />
            <span aria-hidden className="mx-0.5 hidden h-5 border-l border-hairline-strong sm:block" />
            <UserMenu />
          </div>
        </header>
        {/* From 1200 px the open drawer takes its own column, so the page beside it stays whole. */}
        <div data-drawer-open={drawerOpen || undefined} className={cx('flex min-w-0 flex-1 flex-col', drawerOpen && 'lg:pr-[var(--drawer-w)]')}>
          <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1480px] flex-1 px-4 pt-4 pb-24 outline-none sm:px-6 sm:pt-6 sm:pb-12">
            <Outlet />
          </main>
        </div>
      </div>
      <WorkspaceDrawer />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} />
    </div>
  );
}
