import { Link } from '@tanstack/react-router';
import { Palette, PanelLeftClose, PanelLeftOpen, type LucideIcon } from 'lucide-react';
import { Fragment, useEffect, useRef, type ReactNode } from 'react';
import { usePortfolio } from '@/api/hooks';
import { Kbd, Tooltip } from '@/design';
import { cx } from '@/lib/cx';
import { NAV_SECTIONS } from './nav';
import { RAIL_FROM, useMediaQuery, type Rail as RailState } from './useRail';
import { useRunsInProgress } from './useRunsInProgress';
import { Wordmark } from './Wordmark';

interface RailLinkProps {
  to: string;
  label: string;
  icon: LucideIcon;
  current: boolean;
  /** The label is written beside the icon. Otherwise the icon stands alone and a tooltip names it. */
  labelled: boolean;
  /** Extra words for the tooltip and the accessible name: a count or a state. */
  note?: string;
  /** Called when the link is followed: floating labels are put away, also when it leads to the screen already open. */
  onFollow?: () => void;
  /** A count or a mark that belongs to the item. */
  children?: ReactNode;
}

/**
 * One destination. The current one sits on a raised surface with an ink icon: no colour, because
 * cobalt means "you can press this" and iris means "an agent wrote this", and neither is true of where you are.
 */
function RailLink({ to, label, icon: Icon, current, labelled, note, onFollow, children }: RailLinkProps) {
  return (
    <Tooltip side="right" delay={150} disabled={labelled} content={note ? `${label} · ${note}` : label}>
      <Link
        to={to}
        onClick={onFollow}
        aria-current={current ? 'page' : undefined}
        // One clean name for a screen reader: the label, then the count or state when there is one.
        aria-label={note ? `${label}, ${note}` : undefined}
        className={cx(
          'relative flex h-11 items-center justify-center gap-2.5 rounded-sm border text-body t-colors',
          labelled ? 'sm:h-8 sm:justify-start sm:px-2' : 'sm:h-9',
          current
            ? 'border-hairline-strong bg-surface font-semibold text-ink'
            : 'border-transparent bg-canvas font-medium text-ink-700 hover:bg-hover hover:text-ink',
        )}
      >
        <Icon size={16} strokeWidth={current ? 2 : 1.75} aria-hidden className={cx('shrink-0', current ? 'text-ink' : 'text-ink-500')} />
        <span className={labelled ? 'flex-1 whitespace-nowrap' : 'sr-only'}>{label}</span>
        {children}
      </Link>
    </Tooltip>
  );
}

const itemClass = 'min-w-0 flex-1 px-0.5 sm:flex-none sm:px-0';

/**
 * The navigation. From 640 px it is a rail on the left edge, expanded with labels (208 px) or
 * collapsed to icons with tooltips (56 px). Below 640 px it is a bar along the bottom edge.
 *
 * The `nav` holds the place in the layout; the panel inside it is what is drawn. Where the page has no
 * width to give, the place stays 56 px and the labelled panel floats over the page until it is put away.
 */
export function Rail({ pathname, rail }: { pathname: string; rail: RailState }) {
  const portfolio = usePortfolio();
  const openItems = portfolio.data?.work_items.open;
  const running = useRunsInProgress();
  const isRail = useMediaQuery(RAIL_FROM);
  const { floating, dismiss } = rail;
  const collapsed = !rail.expanded;
  const labelled = isRail && !collapsed;
  const place = useRef<HTMLElement>(null);

  // Floating labels are put away by Esc or by a press anywhere outside them. Esc stops here, so the drawer behind stays open.
  useEffect(() => {
    if (!floating) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') return;
      event.stopPropagation();
      dismiss();
    }
    function onPointerDown(event: PointerEvent) {
      if (event.target instanceof Node && !place.current?.contains(event.target)) dismiss();
    }
    window.addEventListener('keydown', onKeyDown, true);
    window.addEventListener('pointerdown', onPointerDown, true);
    return () => {
      window.removeEventListener('keydown', onKeyDown, true);
      window.removeEventListener('pointerdown', onPointerDown, true);
    };
  }, [floating, dismiss]);
  const runsNote = running ? `${running} agent ${running === 1 ? 'run' : 'runs'} in progress` : undefined;
  const toggleName = collapsed ? 'Expand navigation' : 'Collapse navigation';

  return (
    <nav
      ref={place}
      aria-label="Workspace"
      data-rail={collapsed ? 'collapsed' : 'expanded'}
      data-floating={floating || undefined}
      className={cx(
        'rail fixed inset-x-0 bottom-0 z-30 sm:sticky sm:inset-x-auto sm:top-0 sm:bottom-auto sm:h-screen sm:shrink-0',
        floating ? 'sm:z-40' : 'sm:z-auto',
        collapsed || floating ? 'sm:w-[var(--nav-w-rail)]' : 'sm:w-[var(--nav-w)]',
      )}
    >
      <div
        className={cx(
          'rail flex border-t border-hairline-strong bg-canvas px-1 pb-[env(safe-area-inset-bottom)]',
          'sm:h-full sm:flex-col sm:overflow-hidden sm:border-t-0 sm:border-r sm:px-0 sm:pb-0',
          collapsed ? 'sm:w-[var(--nav-w-rail)]' : 'sm:w-[var(--nav-w)]',
          floating && 'sm:absolute sm:inset-y-0 sm:left-0 sm:shadow-raised',
        )}
      >
        <Link
          to="/command-centre"
          onClick={dismiss}
          aria-label="Credit Agent Squad, home"
          className={cx('hidden h-12 shrink-0 items-center border-b border-hairline-strong sm:flex', collapsed ? 'justify-center' : 'px-4')}
        >
          <Wordmark markOnly={collapsed} />
        </Link>

        <ul className="flex h-14 flex-[7] items-center sm:h-auto sm:min-h-0 sm:flex-1 sm:flex-col sm:items-stretch sm:gap-0.5 sm:overflow-y-auto sm:px-2 sm:pt-3">
          {NAV_SECTIONS.map((section, index) => (
            <Fragment key={section.label}>
              {/* A group's name where there is room for words; a rule between groups where there is not. */}
              {labelled ? (
                <li role="presentation" aria-hidden className={cx('eyebrow hidden px-2 pb-1 sm:block', index > 0 && 'pt-4')}>
                  {section.label}
                </li>
              ) : index > 0 ? (
                <li role="presentation" aria-hidden className="mx-2 my-2 hidden border-t border-hairline-strong sm:block" />
              ) : null}
              {section.items.map((item) => {
                const current = pathname.startsWith(item.to);
                const count = item.to === '/command-centre' ? openItems : undefined;
                const runs = item.to === '/agent-activity' ? runsNote : undefined;
                return (
                  <li key={item.to} className={itemClass}>
                    <RailLink
                      to={item.to}
                      label={item.label}
                      icon={item.icon}
                      current={current}
                      labelled={labelled}
                      onFollow={dismiss}
                      note={count !== undefined ? `${count} open ${count === 1 ? 'item' : 'items'}` : runs}
                    >
                      {count !== undefined ? (
                        <span
                          data-open-items
                          className={cx(
                            'tnum',
                            // Beside the label where there is one; otherwise a small figure on the icon's corner, on the item's own ground.
                            labelled ? 'text-caption font-medium' : 'absolute top-[3px] right-[3px] rounded-xs bg-inherit px-0.5 text-micro/3 font-semibold',
                            current ? 'text-ink-700' : 'text-ink-500',
                          )}
                        >
                          {count}
                        </span>
                      ) : null}
                      {runs ? (
                        // A still mark, not a pulse: nothing in the workspace moves for longer than 240 ms.
                        <span
                          data-runs-in-progress
                          role="img"
                          aria-label={runs}
                          title={labelled ? runs : undefined}
                          className={cx('size-1.5 shrink-0 rounded-full bg-iris-mark', labelled ? 'mr-1' : 'absolute top-1.5 right-1.5')}
                        />
                      ) : null}
                    </RailLink>
                  </li>
                );
              })}
            </Fragment>
          ))}
        </ul>

        <div className="flex h-14 min-w-0 flex-1 flex-col justify-center px-0.5 sm:block sm:h-auto sm:flex-none sm:space-y-0.5 sm:px-2 sm:pt-2 sm:pb-3">
          <RailLink to="/design" label="Design system" icon={Palette} current={pathname.startsWith('/design')} labelled={labelled} onFollow={dismiss} />
          <Tooltip
            side="right"
            delay={150}
            disabled={labelled}
            content={
              <span className="inline-flex items-center gap-2">
                {toggleName} <Kbd>[</Kbd>
              </span>
            }
          >
            <button
              type="button"
              data-rail-toggle
              aria-label={toggleName}
              aria-expanded={!collapsed}
              aria-keyshortcuts="["
              onClick={rail.toggle}
              className={cx(
                'hidden w-full items-center justify-center gap-2.5 rounded-sm border border-transparent text-body font-medium text-ink-700 t-colors sm:flex',
                'hover:bg-hover hover:text-ink',
                labelled ? 'h-8 justify-start px-2' : 'h-9',
              )}
            >
              {collapsed ? (
                <PanelLeftOpen size={16} strokeWidth={1.75} aria-hidden className="shrink-0 text-ink-500" />
              ) : (
                <PanelLeftClose size={16} strokeWidth={1.75} aria-hidden className="shrink-0 text-ink-500" />
              )}
              {labelled ? (
                <>
                  <span className="flex-1 text-left whitespace-nowrap">Collapse</span>
                  <span aria-hidden>
                    <Kbd>[</Kbd>
                  </span>
                </>
              ) : null}
            </button>
          </Tooltip>
          {labelled ? (
            <p className="mx-2 mt-3 hidden border-t border-hairline-strong pt-3 text-caption text-pretty text-ink-500 sm:block">
              Synthetic data, for demonstration
            </p>
          ) : null}
        </div>
      </div>
    </nav>
  );
}
