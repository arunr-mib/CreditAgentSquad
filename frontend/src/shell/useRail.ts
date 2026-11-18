import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';

export type RailChoice = 'expanded' | 'collapsed';

/** Where the person's choice is kept, per browser. */
export const RAIL_STORAGE_KEY = 'cas.rail';

/** From this width the navigation is a rail on the left edge; below it, a bar along the bottom. */
export const RAIL_FROM = '(min-width: 640px)';
/**
 * From this width the page is drawn with room for the labelled rail beside it. Below it every screen is laid
 * out for the 56 px rail, so the labels open over the page instead of taking width from it.
 */
const ROOM_FROM = '(min-width: 1200px)';
/** From this width the page has room for the labelled rail and the open drawer together. */
const ROOM_BESIDE_DRAWER_FROM = '(min-width: 1400px)';

function readChoice(): RailChoice | null {
  try {
    const stored = window.localStorage.getItem(RAIL_STORAGE_KEY);
    return stored === 'expanded' || stored === 'collapsed' ? stored : null;
  } catch {
    return null; // storage is off: the choice lasts for this visit only
  }
}

function writeChoice(choice: RailChoice) {
  try {
    window.localStorage.setItem(RAIL_STORAGE_KEY, choice);
  } catch {
    // storage is off: nothing to remember
  }
}

/** Whether the window matches a media query, kept current as it is resized. True where the question cannot be asked. */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (notify: () => void) => {
      if (typeof window.matchMedia !== 'function') return () => {};
      const list = window.matchMedia(query);
      list.addEventListener('change', notify);
      return () => list.removeEventListener('change', notify);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => (typeof window.matchMedia === 'function' ? window.matchMedia(query).matches : true));
}

/** A key pressed while writing belongs to the text, not to the workspace. */
function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return true;
  return target.isContentEditable || target.closest('[contenteditable=""], [contenteditable="true"], [role="textbox"], [role="combobox"]') !== null;
}

export interface Rail {
  /** The labels are showing, beside the page or over it. */
  expanded: boolean;
  /** The labels are showing over the page, because the page has no width to give them. They go away again by themselves. */
  floating: boolean;
  /** Show or hide the labels. Where they sit beside the page, the choice is remembered in this browser. */
  toggle: () => void;
  /** Put floating labels away. Does nothing to labels that sit beside the page. */
  dismiss: () => void;
}

/**
 * The navigation rail's two states from 640 px up: expanded with labels, or collapsed to icons.
 * The toggle button and the `[` key switch between them.
 *
 * Where the page has room (1200 px and wider; 1400 px while the drawer is open) the labelled rail sits
 * beside the page, and the choice is remembered in this browser. Where it has not, the rail beside the
 * page stays at icons whatever the choice, so the page keeps its room, and the labels open over the page
 * until the person goes somewhere, presses Esc or clicks away.
 */
export function useRail(drawerOpen: boolean, pathname: string): Rail {
  const [choice, setChoice] = useState<RailChoice | null>(readChoice);
  const isRail = useMediaQuery(RAIL_FROM);
  const wide = useMediaQuery(ROOM_FROM);
  const wideBesideDrawer = useMediaQuery(ROOM_BESIDE_DRAWER_FROM);
  const room = wide && (!drawerOpen || wideBesideDrawer);

  // Floating labels belong to the moment they were opened in: another screen, the drawer or a resize puts them away.
  const moment = `${pathname}|${drawerOpen}|${room}`;
  const [floatingIn, setFloatingIn] = useState<string | null>(null);
  const floating = !room && floatingIn === moment;
  const expanded = room ? (choice ?? 'expanded') === 'expanded' : floating;

  const toggle = useCallback(() => {
    if (room) {
      const next: RailChoice = expanded ? 'collapsed' : 'expanded';
      writeChoice(next);
      setChoice(next);
    } else {
      setFloatingIn(floating ? null : moment);
    }
  }, [room, expanded, floating, moment]);

  const dismiss = useCallback(() => setFloatingIn(null), []);

  useEffect(() => {
    if (!isRail) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== '[' || event.defaultPrevented || event.repeat || isTyping(event.target)) return;
      // On some keyboards the bracket is typed with AltGr, which reports Ctrl and Alt together.
      const altGr = event.getModifierState?.('AltGraph') ?? false;
      if (!altGr && (event.ctrlKey || event.metaKey || event.altKey)) return;
      toggle();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isRail, toggle]);

  return { expanded, floating, toggle, dismiss };
}
