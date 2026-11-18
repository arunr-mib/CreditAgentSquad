import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { Building2, CalendarClock, ChevronDown, LogOut, Palette, Search } from 'lucide-react';
import { DropdownMenu } from 'radix-ui';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useBorrowers, usePortfolio } from '@/api/hooks';
import { useAuth } from '@/auth/context';
import { CommandPalette, formatDate, Kbd, Popover, Tooltip, useCommandPaletteShortcut, useToast, type Command } from '@/design';
import { roleLabel } from '@/domain/labels';
import { useWorkspaceDrawer } from '@/drawer/context';
import { WorkspaceDrawer } from '@/drawer/WorkspaceDrawer';
import { cx } from '@/lib/cx';
import { STALE_AFTER_DAYS, useAsOf } from './AsOf';
import { Copilot } from './Copilot';
import { NAV } from './nav';
import { Wordmark } from './Wordmark';

const navLinkClass = (current: boolean) =>
  cx(
    'flex h-11 items-center justify-center gap-2.5 rounded-sm text-body t-colors sm:h-8 sm:justify-start sm:px-2.5',
    current ? 'bg-sunken font-semibold text-ink' : 'font-medium text-ink-700 hover:bg-hover hover:text-ink',
  );

function Navigation({ pathname }: { pathname: string }) {
  const portfolio = usePortfolio();
  const openItems = portfolio.data?.work_items.open;
  return (
    <nav
      aria-label="Workspace"
      className="fixed inset-x-0 bottom-0 z-30 flex shrink-0 border-t border-hairline-strong bg-canvas px-1 pb-[env(safe-area-inset-bottom)] sm:sticky sm:inset-x-auto sm:top-0 sm:bottom-auto sm:z-auto sm:h-screen sm:w-14 sm:flex-col sm:border-t-0 sm:border-r sm:px-0 sm:pb-0 lg:w-52"
    >
      <Link to="/command-centre" aria-label="Credit Agent Squad, home" className="hidden h-12 shrink-0 items-center px-[18px] sm:flex lg:px-5">
        <Wordmark />
      </Link>
      <div className="mx-3 hidden border-t border-hairline-strong sm:block lg:mx-5" />
      <ul className="flex h-14 flex-[7] items-center sm:h-auto sm:flex-1 sm:flex-col sm:items-stretch sm:gap-0.5 sm:px-2 sm:pt-3 lg:px-3">
        {NAV.map((item) => {
          const current = pathname.startsWith(item.to);
          const count = item.to === '/command-centre' ? openItems : undefined;
          const Icon = item.icon;
          return (
            <li key={item.to} className="min-w-0 flex-1 px-0.5 sm:flex-none sm:px-0">
              <Tooltip content={item.label} side="right">
                <Link to={item.to} aria-current={current ? 'page' : undefined} className={navLinkClass(current)}>
                  <Icon size={16} strokeWidth={current ? 2 : 1.75} aria-hidden className={cx('shrink-0', current ? 'text-ink' : 'text-ink-500')} />
                  <span className="sr-only flex-1 truncate lg:not-sr-only">{item.label}</span>
                  {count !== undefined ? (
                    <span className="tnum sr-only text-caption font-medium text-ink-500 lg:not-sr-only">
                      {count}
                      <span className="sr-only"> open items</span>
                    </span>
                  ) : null}
                </Link>
              </Tooltip>
            </li>
          );
        })}
      </ul>
      <div className="flex h-14 min-w-0 flex-1 flex-col justify-center px-0.5 sm:block sm:h-auto sm:flex-none sm:px-2 sm:pb-3 lg:px-3">
        <Tooltip content="Design system" side="right">
          <Link to="/design" aria-current={pathname.startsWith('/design') ? 'page' : undefined} className={navLinkClass(pathname.startsWith('/design'))}>
            <Palette size={16} strokeWidth={1.75} aria-hidden className="shrink-0 text-ink-500" />
            <span className="sr-only lg:not-sr-only">Design system</span>
          </Link>
        </Tooltip>
        <div className="mx-2.5 mt-3 hidden border-t border-hairline-strong pt-3 lg:block">
          <p className="text-caption font-medium text-ink-700">Bank of Stoic</p>
          <p className="text-caption text-ink-500">Synthetic data, for demonstration</p>
        </div>
      </div>
    </nav>
  );
}

function AsOfControl() {
  const { asOf, latestDocument, daysSinceLatestDocument } = useAsOf();
  const { can } = useAuth();
  const stale = daysSinceLatestDocument !== null && daysSinceLatestDocument > STALE_AFTER_DAYS;
  return (
    <Popover
      label="Simulated clock"
      align="end"
      className="w-[320px] p-4"
      trigger={
        <button type="button" className="inline-flex h-8 items-center gap-2 rounded-sm px-2 text-body text-ink t-colors hover:bg-hover">
          <CalendarClock size={15} strokeWidth={1.75} aria-hidden className="text-ink-500" />
          <span className="text-ink-500 max-sm:sr-only">As of</span>
          <span data-as-of className="tnum font-medium">
            {asOf ? formatDate(asOf) : 'reading the clock'}
          </span>
          <span className="sr-only">, simulated clock</span>
          {stale ? (
            <span data-stale className="inline-flex items-center gap-1 text-caption font-medium text-amber">
              <span aria-hidden className="size-[7px] rounded-full bg-amber-mark" />
              <span className="sr-only">Data may be out of date: </span>no document for {daysSinceLatestDocument} days
            </span>
          ) : null}
          <ChevronDown size={13} aria-hidden className="text-ink-500 max-sm:hidden" />
        </button>
      }
    >
      <p className="eyebrow">Simulated clock</p>
      <p className="tnum mt-1 text-heading font-semibold text-ink">{asOf ? formatDate(asOf) : 'Not read yet'}</p>
      <p className="mt-1 text-body text-pretty text-ink-700">
        The demonstration runs on a clock that a person sets. Due dates, overdue items and cycle stages follow this date, not today’s.
      </p>
      <p className="eyebrow mt-3">How fresh the data is</p>
      <p data-freshness className={cx('mt-1 text-body text-pretty', stale ? 'font-medium text-amber' : 'text-ink-700')}>
        {latestDocument && daysSinceLatestDocument !== null
          ? `The newest document on file was received ${formatDate(latestDocument)}, ${daysSinceLatestDocument === 0 ? 'the same day as' : `${daysSinceLatestDocument} ${daysSinceLatestDocument === 1 ? 'day' : 'days'} before`} this date.${stale ? ` Nothing has arrived for more than ${STALE_AFTER_DAYS} days, so figures may be out of date.` : ''}`
          : 'No document has been received on or before this date.'}
      </p>
      <p className="mt-2 text-body text-ink-700">
        {can('advance_clock') ? (
          <Link to="/governance" search={{ tab: 'clock' }} className="link font-medium">
            Set the date under Governance
          </Link>
        ) : (
          'An administrator sets the date under Governance.'
        )}
      </p>
    </Popover>
  );
}

function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : '')).toUpperCase();
}

function UserMenu() {
  const { user, signOut } = useAuth();
  const toast = useToast();
  if (!user) return null;
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="inline-flex h-9 items-center gap-2.5 rounded-sm py-1 pr-1.5 pl-1 text-left t-colors hover:bg-hover">
          <span aria-hidden className="flex size-7 items-center justify-center rounded-sm bg-ink text-micro font-semibold tracking-wide text-canvas">
            {initials(user.name)}
          </span>
          <span className="hidden leading-tight md:block">
            <span data-user-name className="block text-caption font-semibold text-ink">
              {user.name}
            </span>
            <span data-user-role className="block text-micro text-ink-500">
              {roleLabel(user.role)}
            </span>
          </span>
          <span className="sr-only md:hidden">
            {user.name}, {roleLabel(user.role)}
          </span>
          <span className="sr-only">Account menu</span>
          <ChevronDown size={13} aria-hidden className="text-ink-500" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className="anim-pop z-50 w-64 rounded-md border border-hairline-strong bg-surface p-1 shadow-raised">
          <DropdownMenu.Label className="px-2 pt-2 pb-2">
            <span className="eyebrow block">Signed in as</span>
            <span className="mt-1 block text-body font-semibold text-ink">{user.name}</span>
            <span className="block text-caption text-ink-700">{user.title}</span>
            <span className="block text-caption break-all text-ink-500">{user.email}</span>
          </DropdownMenu.Label>
          <DropdownMenu.Separator className="my-1 border-t border-hairline" />
          <DropdownMenu.Item
            onSelect={() =>
              void signOut().catch(() =>
                toast({ title: 'Signed out on this device', description: 'The server could not be told; the session will expire by itself.' }),
              )
            }
            className="flex h-8 cursor-pointer items-center gap-2 rounded-xs px-2 text-body text-ink outline-none select-none data-[highlighted]:bg-cobalt-bg"
          >
            <LogOut size={14} aria-hidden className="text-ink-500" />
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export function AppShell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const navigate = useNavigate();
  const borrowers = useBorrowers();
  const [paletteOpen, setPaletteOpen] = useState(false);
  useCommandPaletteShortcut(useCallback(() => setPaletteOpen((open) => !open), []));
  const drawer = useWorkspaceDrawer();
  const { open: drawerOpen, tab: drawerTab, openCopilot, close: closeDrawer } = drawer;
  // Ctrl or Cmd + J: the Copilot, scoped to the borrower on screen when there is one.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'j') return;
      event.preventDefault();
      if (drawerOpen && drawerTab === 'copilot') closeDrawer();
      else {
        const code = pathname.match(/^\/borrowers\/([^/]+)/)?.[1];
        openCopilot(code ? { kind: 'borrower', code } : undefined);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen, drawerTab, openCopilot, closeDrawer, pathname]);

  const commands = useMemo<Command[]>(() => {
    const go = (to: string) => () => void navigate({ to });
    return [
      ...NAV.map((item) => ({
        id: `nav-${item.to}`,
        group: 'Go to',
        label: item.label,
        hint: item.description,
        icon: <item.icon size={15} strokeWidth={1.75} />,
        run: go(item.to),
      })),
      {
        id: 'nav-design',
        group: 'Go to',
        label: 'Design system',
        hint: 'Tokens and components',
        icon: <Palette size={15} strokeWidth={1.75} />,
        run: go('/design'),
      },
      ...(borrowers.data ?? []).map((borrower) => ({
        id: `borrower-${borrower.id}`,
        group: 'Borrowers',
        label: borrower.name,
        hint: borrower.industry,
        icon: <Building2 size={15} strokeWidth={1.75} />,
        keywords: `${borrower.code} ${borrower.analyst ?? ''} ${borrower.relationship_manager ?? ''}`,
        run: () => void navigate({ to: '/borrowers/$code', params: { code: borrower.code } }),
      })),
    ];
  }, [navigate, borrowers.data]);

  return (
    <div className="flex min-h-screen bg-canvas">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[70] focus:rounded-sm focus:bg-surface focus:px-3 focus:py-1.5 focus:text-body focus:font-medium focus:text-cobalt"
      >
        Skip to content
      </a>
      <Navigation pathname={pathname} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="@container sticky top-0 z-30 flex h-12 shrink-0 items-center justify-between gap-2 border-b border-hairline-strong bg-canvas px-4 sm:gap-4 sm:px-6">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex size-8 shrink-0 items-center justify-center gap-2 rounded-sm border border-hairline-strong bg-surface text-body text-ink-500 t-colors hover:border-ink-400 hover:text-ink-700 @min-[680px]:w-[340px] @min-[680px]:justify-start @min-[680px]:px-2.5 [&>span]:sr-only @min-[680px]:[&>span]:not-sr-only"
            aria-keyshortcuts="Control+K Meta+K"
          >
            <Search size={14} aria-hidden />
            <span className="flex-1 text-left">Search borrowers and commands</span>
            <span aria-hidden>
              <Kbd>Ctrl K</Kbd>
            </span>
          </button>
          <div className="flex min-w-0 items-center gap-1 sm:gap-2">
            <Copilot />
            <AsOfControl />
            <span aria-hidden className="mx-1 hidden h-5 border-l border-hairline-strong sm:block" />
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
