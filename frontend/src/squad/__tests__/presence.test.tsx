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
    for (const selector of ['.sq-orbit', '.sq-core-breathe', '.sq-ripple']) expect(block).toContain(selector);
    expect(block).toMatch(/animation:\s*none/);
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
});
