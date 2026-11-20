// frontend/src/squad/evidence/EvidenceResizer.tsx
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSource } from '@/source/context';

const MIN = 360;
const MAX = 760;
const STEP = 24;
const KEY = 'squad.source.w';

export function clampWidth(px: number, viewport: number): number {
  return Math.round(Math.max(MIN, Math.min(px, MAX, viewport * 0.6)));
}

function initialWidth(): number {
  try {
    const stored = Number(localStorage.getItem(KEY));
    if (stored > 0) return clampWidth(stored, window.innerWidth);
  } catch {
    /* ignore */
  }
  const fromCss = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--source-w'), 10);
  return clampWidth(Number.isFinite(fromCss) ? fromCss : 590, window.innerWidth);
}

/** A handle on the evidence drawer's left edge. The drawer itself is the reused SourceDrawer; this only sets its width. */
export function EvidenceResizer() {
  const { current } = useSource();
  const [width, setWidth] = useState(initialWidth);
  const dragging = useRef(false);

  const apply = useCallback((px: number) => {
    const next = clampWidth(px, window.innerWidth);
    setWidth(next);
    document.documentElement.style.setProperty('--source-w', `${next}px`);
    try {
      localStorage.setItem(KEY, String(next));
    } catch {
      /* not remembered */
    }
  }, []);

  useEffect(() => {
    if (current) document.documentElement.style.setProperty('--source-w', `${width}px`);
  }, [current, width]);

  useEffect(() => {
    const move = (event: PointerEvent) => dragging.current && apply(window.innerWidth - event.clientX);
    const up = () => {
      dragging.current = false;
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
  }, [apply]);

  if (!current) return null;
  return (
    // A focusable vertical separator is the WAI-ARIA window splitter: it is interactive, which the lint rule cannot tell.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize the evidence"
      aria-valuemin={MIN}
      aria-valuemax={Math.min(MAX, Math.round(window.innerWidth * 0.6))}
      aria-valuenow={width}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      className="sq-resizer"
      style={{ right: `${width}px` }}
      onPointerDown={() => {
        dragging.current = true;
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
