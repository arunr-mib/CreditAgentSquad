// frontend/src/squad/evidence/EvidenceResizer.tsx
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSource } from '@/source/context';

const MIN = 360;
const MAX = 760;
const STEP = 24;
const KEY = 'squad.source.w';
/** The conversation keeps at least this much beside the drawer (after the nav). */
const CONVERSATION_MIN = 480;

/** The drawer's width: at least 360 px, at most 760 px, 60 percent of the window, and (given the nav's width) leaving the conversation 480 px. */
export function clampWidth(px: number, viewport: number, navWidth?: number): number {
  const room = navWidth === undefined ? Infinity : viewport - navWidth - CONVERSATION_MIN;
  return Math.round(Math.max(MIN, Math.min(px, MAX, viewport * 0.6, room)));
}

function initialPreferred(): number {
  try {
    const stored = Number(localStorage.getItem(KEY));
    if (stored > 0) return stored;
  } catch {
    /* ignore */
  }
  const fromCss = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--source-w'), 10);
  return Number.isFinite(fromCss) ? fromCss : 590;
}

/** A handle on the evidence drawer's left edge. The drawer itself is the reused SourceDrawer; this only sets its width. */
export function EvidenceResizer({ navWidth }: { navWidth?: number } = {}) {
  const { current } = useSource();
  const open = current !== null;
  const [preferred, setPreferred] = useState(initialPreferred);
  const [viewport, setViewport] = useState(() => window.innerWidth);
  const dragging = useRef(false);
  const width = clampWidth(preferred, viewport, navWidth);

  const apply = useCallback((px: number) => {
    const next = clampWidth(px, window.innerWidth, navWidth);
    setPreferred(next);
    try {
      localStorage.setItem(KEY, String(next));
    } catch {
      /* not remembered */
    }
  }, [navWidth]);

  // The width follows the window: a resize re-clamps what the person chose without forgetting it.
  useEffect(() => {
    const onResize = () => setViewport(window.innerWidth);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    if (!open) return;
    document.documentElement.style.setProperty('--source-w', `${width}px`);
    return () => {
      document.documentElement.style.removeProperty('--source-w');
    };
  }, [open, width]);

  useEffect(() => {
    const move = (event: PointerEvent) => dragging.current && apply(window.innerWidth - event.clientX);
    const stop = () => {
      dragging.current = false;
      document.body.style.removeProperty('user-select');
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
      stop();
    };
  }, [apply]);

  if (!open) return null;
  return (
    // A focusable vertical separator is the WAI-ARIA window splitter: it is interactive, which the lint rule cannot tell.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize the evidence"
      aria-valuemin={MIN}
      aria-valuemax={clampWidth(MAX, viewport, navWidth)}
      aria-valuenow={width}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      className="sq-resizer"
      style={{ right: `${width}px` }}
      onPointerDown={(event) => {
        dragging.current = true;
        document.body.style.setProperty('user-select', 'none');
        try {
          event.currentTarget.setPointerCapture?.(event.pointerId);
        } catch {
          /* capture is a nicety */
        }
      }}
      onKeyDown={(e) => {
        if (e.key === 'ArrowLeft') apply(width + STEP);
        else if (e.key === 'ArrowRight') apply(width - STEP);
        else if (e.key === 'Home') apply(MAX);
        else if (e.key === 'End') apply(MIN);
        else return;
        e.preventDefault();
      }}
    />
  );
}
