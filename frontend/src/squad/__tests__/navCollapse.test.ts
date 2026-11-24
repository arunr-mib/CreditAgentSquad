import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useNavCollapse } from '../shell/useNavCollapse';

function setWidth(px: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: px });
  act(() => void window.dispatchEvent(new Event('resize')));
}

describe('useNavCollapse', () => {
  beforeEach(() => {
    localStorage.setItem('squad.nav.collapsed', 'false');
    setWidth(1100);
  });

  it('folds the nav under an open drawer below 1280 px and restores the choice on close', () => {
    const { result, rerender } = renderHook(({ open }) => useNavCollapse(open), { initialProps: { open: false } });
    expect(result.current.collapsed).toBe(false);
    rerender({ open: true });
    expect(result.current.collapsed).toBe(true);
    rerender({ open: false });
    expect(result.current.collapsed).toBe(false);
  });

  it('expands at once when the toggle is pressed while folded, without changing the stored choice, until the drawer closes', () => {
    const { result, rerender } = renderHook(({ open }) => useNavCollapse(open), { initialProps: { open: true } });
    expect(result.current.collapsed).toBe(true);
    act(() => result.current.toggle());
    expect(result.current.collapsed).toBe(false);
    expect(localStorage.getItem('squad.nav.collapsed')).toBe('false');
    act(() => result.current.toggle());
    expect(result.current.collapsed).toBe(true);
    act(() => result.current.toggle());
    rerender({ open: false });
    rerender({ open: true });
    expect(result.current.collapsed).toBe(true);
  });

  it('does not fold at 1280 px or wider', () => {
    setWidth(1400);
    const { result } = renderHook(() => useNavCollapse(true));
    expect(result.current.collapsed).toBe(false);
  });
});
