import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';

export type RailChoice = 'expanded' | 'collapsed';

/** Where the person's choice is kept, per browser. */
export const RAIL_STORAGE_KEY = 'cas.rail';

/** From this width the navigation is a rail on the left edge; below it, a bar along the bottom. */
export const RAIL_FROM = '(min-width: 640px)';
/** From this width the rail starts with its labels, until the person chooses otherwise. */
const LABELS_FROM = '(min-width: 1200px)';
/** From this width the page has room for the rail's labels and the open drawer together. */
const BESIDE_DRAWER_FROM = '(min-width: 1400px)';

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
  /** What is shown now. */
  collapsed: boolean;
  /** The drawer is open on a window too narrow for both, so the rail is held collapsed whatever the choice. */
  held: boolean;
  /** Switch between labels and icons, and remember it. Does nothing while the rail is held. */
  toggle: () => void;
}

/**
 * The navigation rail's two states from 640 px up: expanded with labels, or collapsed to icons.
 * The toggle button and the `[` key switch between them; the choice is remembered in this browser.
 */
export function useRail(drawerOpen: boolean): Rail {
  const [choice, setChoice] = useState<RailChoice | null>(readChoice);
  const isRail = useMediaQuery(RAIL_FROM);
  const roomForLabels = useMediaQuery(LABELS_FROM);
  const roomBesideDrawer = useMediaQuery(BESIDE_DRAWER_FROM);

  const held = drawerOpen && !roomBesideDrawer;
  const collapsed = held || (choice ?? (roomForLabels ? 'expanded' : 'collapsed')) === 'collapsed';

  const toggle = useCallback(() => {
    if (held) return;
    const next: RailChoice = collapsed ? 'expanded' : 'collapsed';
    writeChoice(next);
    setChoice(next);
  }, [held, collapsed]);

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

  return { collapsed, held, toggle };
}
