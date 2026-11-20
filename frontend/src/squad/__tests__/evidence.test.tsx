// frontend/src/squad/__tests__/evidence.test.tsx
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import css from '../squad.css?raw';
import { applyLook, clearLook, contrast, legacyTokens, LOOKS, LOOK_IDS } from '../looks';
import tokens from '@/design/tokens.css?raw';
import drawerSrc from '@/source/SourceDrawer.tsx?raw';
import pdfSrc from '@/source/PdfPage.tsx?raw';
import changeSrc from '@/source/ChangeFigure.tsx?raw';
import agentSrc from '@/source/AgentBody.tsx?raw';
import calcSrc from '@/source/CalculationBreakdown.tsx?raw';
import figureSrc from '@/design/Figure.tsx?raw';
import { clampWidth, EvidenceResizer } from '../evidence/EvidenceResizer';

const source = vi.hoisted(() => ({ current: null as unknown }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: () => {}, close: () => {}, current: source.current }) }));

describe('clampWidth', () => {
  it('keeps the drawer between 360 px and the smaller of 760 px and 60 percent of the window', () => {
    expect(clampWidth(100, 1400)).toBe(360);
    expect(clampWidth(2000, 1400)).toBe(760);
    expect(clampWidth(2000, 1000)).toBe(600);
    expect(clampWidth(500, 1400)).toBe(500);
  });
});

describe('clampWidth with the nav', () => {
  it('leaves the conversation at least 480 px after the nav', () => {
    expect(clampWidth(600, 1400, 64)).toBe(600);
    expect(clampWidth(760, 1100, 64)).toBe(556);
    expect(clampWidth(760, 1000, 64)).toBe(456);
    expect(clampWidth(760, 1000, 248)).toBe(360); // cannot honour both: the minimum wins, the shell folds the nav
  });
});

describe('EvidenceResizer', () => {
  beforeEach(() => {
    source.current = null;
    document.documentElement.style.removeProperty('--source-w');
    localStorage.clear();
  });

  it('is absent while no evidence is open', () => {
    render(<EvidenceResizer />);
    expect(screen.queryByRole('separator')).not.toBeInTheDocument();
  });

  it('widens the drawer with ArrowLeft (the edge moves left), narrows it with ArrowRight, and remembers the width', async () => {
    source.current = { type: 'fact', id: 'f1' };
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1400 });
    render(<EvidenceResizer />);
    const handle = screen.getByRole('separator', { name: /resize the evidence/i });
    handle.focus();
    const before = Number(handle.getAttribute('aria-valuenow'));
    await userEvent.keyboard('{ArrowLeft}');
    expect(Number(handle.getAttribute('aria-valuenow'))).toBe(before + 24);
    expect(document.documentElement.style.getPropertyValue('--source-w')).toBe(`${before + 24}px`);
    expect(localStorage.getItem('squad.source.w')).toBe(String(before + 24));
    await userEvent.keyboard('{End}');
    expect(handle.getAttribute('aria-valuenow')).toBe('360');
  });

  it('re-clamps when the window shrinks and clears --source-w on close', () => {
    source.current = { type: 'fact', id: 'f1' };
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1400 });
    localStorage.setItem('squad.source.w', '700');
    const { rerender } = render(<EvidenceResizer navWidth={64} />);
    const handle = screen.getByRole('separator');
    expect(handle.getAttribute('aria-valuenow')).toBe('700');
    act(() => {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1000 });
      window.dispatchEvent(new Event('resize'));
    });
    expect(handle.getAttribute('aria-valuenow')).toBe('456');
    expect(handle.getAttribute('aria-valuemax')).toBe('456');
    expect(document.documentElement.style.getPropertyValue('--source-w')).toBe('456px');
    source.current = null;
    rerender(<EvidenceResizer navWidth={64} />);
    expect(document.documentElement.style.getPropertyValue('--source-w')).toBe('');
  });

  it('never goes below the minimum however far it is dragged', () => {
    source.current = { type: 'fact', id: 'f1' };
    render(<EvidenceResizer />);
    const handle = screen.getByRole('separator');
    act(() => {
      handle.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 800 }));
      window.dispatchEvent(new PointerEvent('pointermove', { clientX: 5000 }));
      window.dispatchEvent(new PointerEvent('pointerup'));
    });
    expect(Number(handle.getAttribute('aria-valuenow'))).toBeGreaterThanOrEqual(360);
  });
});

describe('the evidence drawer follows the look', () => {
  it.each(LOOK_IDS)('%s: the reused drawer reads the look\'s own surface and ink', (id) => {
    const el = document.createElement('div');
    applyLook(id, el);
    const root = el.style;
    expect(root.getPropertyValue('--surface')).toBe(LOOKS[id].vars.surface);
    expect(root.getPropertyValue('--ink-900')).toBe(LOOKS[id].vars.ink);
    expect(root.getPropertyValue('--green')).toBe(LOOKS[id].vars.ok);
    expect(document.documentElement.style.getPropertyValue('--surface')).toBe('');
    clearLook(el);
    expect(root.getPropertyValue('--surface')).toBe('');
    expect(root.getPropertyValue('--ink-900')).toBe('');
    expect(contrast(LOOKS[id].vars.ink2, LOOKS[id].vars.surface)).toBeGreaterThanOrEqual(4.5);
  });

  it('pushes the conversation aside from 1000 px, not only from 1200 px', () => {
    expect(css).toMatch(/@media \(min-width: 1000px\)\s*\{\s*html\[data-source-open\] \.sq-stage/);
  });

  it('keeps evidence documents on paper in every look', () => {
    expect(css).toMatch(/\[data-source-drawer\] canvas[^{]*\[data-pdf-page\][^{]*\{[^}]*background:\s*var\(--sq-paper\)/);
    expect(css).toMatch(/\[data-pdf-page\] p\s*\{[^}]*color:\s*var\(--sq-paper-ink\)/);
  });

  it('bridges every legacy token the drawer, figures and page use', () => {
    const colourOf = new Map<string, string>();
    for (const m of tokens.matchAll(/--color-([a-z0-9-]+):\s*var\((--[a-z0-9-]+)\)/g)) colourOf.set(m[1]!, m[2]!);
    const bridged = Object.keys(legacyTokens('night'));
    const used = new Set<string>();
    for (const src of [drawerSrc, pdfSrc, changeSrc, agentSrc, calcSrc, figureSrc]) {
      for (const m of src.matchAll(/\b(?:bg|text|border|ring|fill|stroke)-([a-z0-9]+(?:-[a-z0-9]+)*)/g)) {
        const token = colourOf.get(m[1]!);
        if (token) used.add(token);
      }
    }
    expect(used.size).toBeGreaterThan(10);
    expect([...used].filter((t) => !bridged.includes(t))).toEqual([]);
  });

  it.each(LOOK_IDS)('%s: the quote highlight (ink on the soft ground) and link hover read at 4.5:1', (id) => {
    const v = legacyTokens(id);
    expect(contrast(LOOKS[id].vars.ink, v['--cobalt-bg']!)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(v['--cobalt-strong']!, v['--cobalt-bg']!)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(v['--ink-700']!, v['--surface']!)).toBeGreaterThanOrEqual(4.5);
  });
});
