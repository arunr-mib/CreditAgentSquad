// frontend/src/squad/__tests__/evidence.test.tsx
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import css from '../squad.css?raw';
import { applyLook, clearLook, contrast, LOOKS, LOOK_IDS } from '../looks';
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

  it('moves the edge with the arrow keys and remembers the width', async () => {
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
    expect(css).toMatch(/\[data-source-drawer\] canvas[^{]*\{[^}]*background:\s*var\(--sq-paper\)/);
  });
});
