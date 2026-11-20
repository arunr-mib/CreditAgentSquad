// frontend/src/squad/__tests__/presence.test.tsx
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import css from '../squad.css?raw';
import { SquadMark } from '../mark/SquadMark';
import { PresenceLine, PresenceProvider, usePresence } from '../presence/Presence';

describe('SquadMark', () => {
  it('draws four dots around one core in every state', () => {
    for (const state of ['rest', 'working', 'needs', 'responding'] as const) {
      const { container, unmount } = render(<SquadMark state={state} />);
      expect(container.querySelectorAll('circle.sq-dot')).toHaveLength(4);
      expect(container.querySelectorAll('circle.sq-core')).toHaveLength(1);
      expect(container.querySelector('svg')).toHaveAttribute('data-state', state);
      unmount();
    }
  });

  it('shows the ember ring only when the squad needs you', () => {
    const needs = render(<SquadMark state="needs" />);
    expect(needs.container.querySelector('circle.sq-core')).toHaveAttribute('stroke', 'var(--sq-ember)');
    needs.unmount();
    const rest = render(<SquadMark state="rest" />);
    expect(rest.container.querySelector('circle.sq-core')).not.toHaveAttribute('stroke');
  });

  it('is hidden from assistive tech unless it has a label', () => {
    const { container, rerender } = render(<SquadMark />);
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    rerender(<SquadMark label="Credit Squad" />);
    expect(screen.getByRole('img', { name: 'Credit Squad' })).toBeInTheDocument();
  });

  it('turns every movement off under reduced motion', () => {
    const block = css.slice(css.indexOf('@media (prefers-reduced-motion: reduce)'));
    for (const selector of ['.sq-orbit', '.sq-core-breathe', '.sq-ripple', '.sq-mk-responding .sq-orbit']) {
      const rule = new RegExp(`${selector.replace(/[.]/g, '\\.')}[^{}]*\\{[^}]*animation:\\s*none`);
      expect(block).toMatch(rule);
    }
  });
});

function Controls() {
  const p = usePresence();
  return (
    <>
      <button onClick={() => p.say('Recorded as Priya')}>say</button>
      <button
        onClick={() => {
          const end = p.beginWork();
          (window as unknown as { end: () => void }).end = end;
        }}
      >
        work
      </button>
      <button onClick={() => p.pulse()}>pulse</button>
    </>
  );
}
const mount = (needs = 0) =>
  render(
    <PresenceProvider needs={needs}>
      <PresenceLine />
      <Controls />
    </PresenceProvider>,
  );
const mark = () => document.querySelector('svg[data-state]') as SVGElement;

describe('presence line', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('always has a reserved status line, empty until Squad says something', () => {
    mount();
    expect(screen.getByRole('status')).toHaveTextContent('');
    act(() => screen.getByText('say').click());
    expect(screen.getByRole('status')).toHaveTextContent('Recorded as Priya');
    act(() => void vi.advanceTimersByTime(6100));
    expect(screen.getByRole('status')).toHaveTextContent('');
  });

  it('names the product "Credit Squad" and says its state in words', () => {
    mount(2);
    expect(screen.getByText('Credit Squad')).toBeInTheDocument();
    expect(screen.getByText(/needs you/i)).toBeInTheDocument();
    expect(mark()).toHaveAttribute('data-state', 'needs');
  });

  it('is working while work is under way and returns to needs-you afterwards', () => {
    mount(1);
    act(() => screen.getByText('work').click());
    expect(mark()).toHaveAttribute('data-state', 'working');
    act(() => (window as unknown as { end: () => void }).end());
    expect(mark()).toHaveAttribute('data-state', 'needs');
  });

  it('responds briefly and then settles', () => {
    mount(0);
    act(() => screen.getByText('pulse').click());
    expect(mark()).toHaveAttribute('data-state', 'responding');
    act(() => void vi.advanceTimersByTime(1000));
    expect(mark()).toHaveAttribute('data-state', 'rest');
  });

  it('unmount clears a pending say timer', () => {
    const spy = vi.spyOn(globalThis, 'clearTimeout');
    const { unmount } = mount();
    act(() => screen.getByText('say').click());
    unmount();
    expect(spy).toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
    spy.mockRestore();
  });

  it('a second say replaces the first and the first timer does not blank it', () => {
    function Two() {
      const p = usePresence();
      return (
        <>
          <button onClick={() => p.say('first')}>one</button>
          <button onClick={() => p.say('second')}>two</button>
        </>
      );
    }
    render(
      <PresenceProvider needs={0}>
        <PresenceLine />
        <Two />
      </PresenceProvider>,
    );
    act(() => screen.getByText('one').click());
    act(() => void vi.advanceTimersByTime(4000));
    act(() => screen.getByText('two').click());
    expect(screen.getByRole('status')).toHaveTextContent('second');
    act(() => void vi.advanceTimersByTime(3000));
    expect(screen.getByRole('status')).toHaveTextContent('second');
    act(() => void vi.advanceTimersByTime(3100));
    expect(screen.getByRole('status')).toHaveTextContent('');
  });

  it('nested work stays working until both disposers run; a disposer twice is harmless', () => {
    const ends: Array<() => void> = [];
    function Nest() {
      const p = usePresence();
      return <button onClick={() => ends.push(p.beginWork())}>begin</button>;
    }
    render(
      <PresenceProvider needs={0}>
        <PresenceLine />
        <Nest />
      </PresenceProvider>,
    );
    act(() => screen.getByText('begin').click());
    act(() => screen.getByText('begin').click());
    act(() => ends[0]?.());
    act(() => ends[0]?.());
    expect(mark()).toHaveAttribute('data-state', 'working');
    act(() => ends[1]?.());
    expect(mark()).toHaveAttribute('data-state', 'rest');
  });

  it('moves between rest and needs when the needs count changes', () => {
    const ui = (n: number) => (
      <PresenceProvider needs={n}>
        <PresenceLine />
      </PresenceProvider>
    );
    const { rerender } = render(ui(0));
    expect(mark()).toHaveAttribute('data-state', 'rest');
    rerender(ui(3));
    expect(mark()).toHaveAttribute('data-state', 'needs');
    rerender(ui(0));
    expect(mark()).toHaveAttribute('data-state', 'rest');
  });

  it('a second pulse while responding restarts the turn and the ripple', () => {
    mount();
    act(() => screen.getByText('pulse').click());
    const first = document.querySelector('.sq-ripple');
    act(() => void vi.advanceTimersByTime(500));
    act(() => screen.getByText('pulse').click());
    expect(document.querySelector('.sq-ripple')).not.toBe(first);
    expect(document.querySelector('.sq-mk-responding .sq-orbit')).not.toBeNull();
    act(() => void vi.advanceTimersByTime(600));
    expect(mark()).toHaveAttribute('data-state', 'responding');
    act(() => void vi.advanceTimersByTime(400));
    expect(mark()).toHaveAttribute('data-state', 'rest');
  });

  it('announces state changes through one polite live region without a second status role', () => {
    mount(1);
    expect(screen.getAllByRole('status')).toHaveLength(1);
    expect(document.querySelector('.sq-sr[aria-live="polite"]')).toHaveTextContent(/needs you/i);
  });
});
