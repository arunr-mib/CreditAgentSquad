import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { Building2, CalendarClock, Check, ChevronDown, Palette, Search } from 'lucide-react';
import { DropdownMenu } from 'radix-ui';
import { useCallback, useMemo, useState } from 'react';
import { Button, CommandPalette, formatDate, Kbd, Popover, Tooltip, useCommandPaletteShortcut, type Command } from '@/design';
import { workItems } from '@/fixtures/workItems';
import { cx } from '@/lib/cx';
import { useAsOf } from './AsOf';
import { NAV } from './nav';
import { Wordmark } from './Wordmark';

const ROLES = ['Analyst', 'Portfolio manager', 'Credit officer', 'Credit administrator', 'Credit review'] as const;

function Navigation({ pathname }: { pathname: string }) {
  return (
    <nav aria-label="Workspace" className="sticky top-0 flex h-screen w-14 shrink-0 flex-col border-r border-hairline-strong bg-canvas lg:w-52">
      <Link to="/showcase/command-centre" aria-label="Credit Agent Squad, home" className="flex h-12 shrink-0 items-center px-[18px] lg:px-5">
        <Wordmark />
      </Link>
      <div className="mx-3 border-t border-hairline-strong lg:mx-5" />
      <ul className="flex flex-1 flex-col gap-0.5 px-2 pt-3 lg:px-3">
        {NAV.map((item) => {
          const current = item.match.some((path) => pathname.startsWith(path));
          const count = item.to === '/showcase/command-centre' ? workItems.length : undefined;
          const Icon = item.icon;
          return (
            <li key={item.to}>
              <Tooltip content={item.label} side="right">
                <Link
                  to={item.to}
                  aria-current={current ? 'page' : undefined}
                  className={cx(
                    'flex h-8 items-center gap-2.5 rounded-sm px-2.5 text-body t-colors',
                    current ? 'bg-sunken font-semibold text-ink' : 'font-medium text-ink-700 hover:bg-hover hover:text-ink',
                  )}
                >
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
      <div className="px-2 pb-3 lg:px-3">
        <Tooltip content="Design system" side="right">
          <Link
            to="/design"
            aria-current={pathname.startsWith('/design') ? 'page' : undefined}
            className={cx(
              'flex h-8 items-center gap-2.5 rounded-sm px-2.5 text-body t-colors',
              pathname.startsWith('/design') ? 'bg-sunken font-semibold text-ink' : 'font-medium text-ink-700 hover:bg-hover hover:text-ink',
            )}
          >
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
  const { asOf, advanceDays, reset } = useAsOf();
  return (
    <Popover
      label="Simulated clock"
      align="end"
      className="w-[320px] p-4"
      trigger={
        <button type="button" className="inline-flex h-8 items-center gap-2 rounded-sm px-2 text-body text-ink t-colors hover:bg-hover">
          <CalendarClock size={15} strokeWidth={1.75} aria-hidden className="text-ink-500" />
          <span className="text-ink-500">As of</span>
          <span className="tnum font-medium">{formatDate(asOf)}</span>
          <span className="sr-only">, simulated clock. Change the date.</span>
          <ChevronDown size={13} aria-hidden className="text-ink-500" />
        </button>
      }
    >
      <p className="eyebrow">Simulated clock</p>
      <p className="tnum mt-1 text-heading font-semibold text-ink">{formatDate(asOf)}</p>
      <p className="mt-1 text-body text-ink-700">
        The demonstration runs on a clock that a person advances. Due dates, overdue items and cycle stages follow this date, not today’s.
      </p>
      <div className="mt-3 flex items-center gap-2">
        <Button size="sm" onClick={() => advanceDays(1)}>
          Advance one day
        </Button>
        <Button size="sm" onClick={() => advanceDays(7)}>
          One week
        </Button>
        <Button size="sm" variant="ghost" onClick={reset}>
          Reset
        </Button>
      </div>
    </Popover>
  );
}

function UserMenu() {
  const [role, setRole] = useState<string>('Portfolio manager');
  const itemClass =
    'flex h-8 cursor-pointer items-center justify-between gap-6 rounded-xs px-2 text-body text-ink outline-none select-none data-[highlighted]:bg-cobalt-bg';
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="inline-flex h-9 items-center gap-2.5 rounded-sm py-1 pr-1.5 pl-1 text-left t-colors hover:bg-hover">
          <span aria-hidden className="flex size-7 items-center justify-center rounded-sm bg-ink text-micro font-semibold tracking-wide text-canvas">
            MO
          </span>
          <span className="hidden leading-tight md:block">
            <span className="block text-caption font-semibold text-ink">Maya Okafor</span>
            <span className="block text-micro text-ink-500">{role}</span>
          </span>
          <span className="sr-only md:hidden">Maya Okafor, {role}</span>
          <span className="sr-only">Account menu</span>
          <ChevronDown size={13} aria-hidden className="text-ink-500" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className="anim-pop z-50 w-60 rounded-md border border-hairline-strong bg-surface p-1 shadow-raised">
          <DropdownMenu.Label className="eyebrow px-2 pt-2 pb-1">Acting as</DropdownMenu.Label>
          <DropdownMenu.RadioGroup value={role} onValueChange={setRole}>
            {ROLES.map((option) => (
              <DropdownMenu.RadioItem key={option} value={option} className={itemClass}>
                {option}
                <DropdownMenu.ItemIndicator>
                  <Check size={14} aria-hidden className="text-cobalt" />
                </DropdownMenu.ItemIndicator>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
          <DropdownMenu.Separator className="my-1 border-t border-hairline" />
          <DropdownMenu.Item className={itemClass}>Sign out</DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export function AppShell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);
  useCommandPaletteShortcut(useCallback(() => setPaletteOpen((open) => !open), []));

  const commands = useMemo<Command[]>(() => {
    const go = (to: string) => () => void navigate({ to });
    const borrowers = [...new Map(workItems.map((item) => [item.borrowerId, item])).values()];
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
        id: 'nav-spread',
        group: 'Go to',
        label: 'Spread grid',
        hint: 'Brightwater Fastener Co.',
        icon: <Building2 size={15} strokeWidth={1.75} />,
        keywords: 'spreads financials',
        run: go('/showcase/spread'),
      },
      {
        id: 'nav-design',
        group: 'Go to',
        label: 'Design system',
        hint: 'Tokens and components',
        icon: <Palette size={15} strokeWidth={1.75} />,
        run: go('/design'),
      },
      ...borrowers.map((item) => ({
        id: `borrower-${item.borrowerId}`,
        group: 'Borrowers',
        label: item.borrowerName,
        hint: item.borrowerId,
        icon: <Building2 size={15} strokeWidth={1.75} />,
        keywords: item.summary,
        run: go(item.borrowerId === 'BRW-0417' ? '/showcase/covenants' : '/showcase/command-centre'),
      })),
    ];
  }, [navigate]);

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
        <header className="sticky top-0 z-30 flex h-12 shrink-0 items-center justify-between gap-4 border-b border-hairline-strong bg-canvas px-6">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex h-8 w-[340px] items-center gap-2 rounded-sm border border-hairline-strong bg-surface px-2.5 text-body text-ink-500 t-colors hover:border-ink-400 hover:text-ink-700"
            aria-keyshortcuts="Control+K Meta+K"
          >
            <Search size={14} aria-hidden />
            <span className="flex-1 text-left">Search borrowers, loans and commands</span>
            <span aria-hidden>
              <Kbd>Ctrl K</Kbd>
            </span>
          </button>
          <div className="flex items-center gap-3">
            <AsOfControl />
            <span aria-hidden className="h-5 border-l border-hairline-strong" />
            <UserMenu />
          </div>
        </header>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1480px] flex-1 px-6 pt-6 pb-12 outline-none">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} />
    </div>
  );
}
