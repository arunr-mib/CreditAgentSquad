import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SignalList } from './SignalList';

vi.mock('../DocType', () => ({ useSignalWords: () => (rule: string) => ({ runway_below_watch: 'Runway below the watch level' })[rule] ?? rule }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));

const s = (id: string, period_end: string, subject: string | null = 'min_runway_months', rule_id = 'runway_below_watch') =>
  ({ id, rule_id, severity: 'high' as const, period_end, explanation: { text: `Words for ${period_end}` }, basis: { subject } });

describe('SignalList', () => {
  it('shows one line for a rule that fired in many periods, with the count, the range and each period on request', () => {
    render(<SignalList signals={[s('a', '2026-08-31'), s('b', '2026-10-31'), s('c', '2026-09-30')]} />);
    const top = screen.getAllByRole('listitem')[0];
    expect(top).toHaveTextContent('Runway below the watch level · min runway months · 3 periods, 31 Aug 2026 to 31 Oct 2026');
    expect(screen.getAllByText('Runway below the watch level')).toHaveLength(1);
    expect(within(screen.getByRole('group')).getAllByRole('listitem')).toHaveLength(3);
  });

  it('keeps a single signal as one plain line, and separate lines for separate covenants', () => {
    render(<SignalList signals={[s('a', '2026-10-31'), s('b', '2026-10-31', 'min_unrestricted_cash')]} />);
    expect(screen.getAllByText('Runway below the watch level')).toHaveLength(2);
    expect(screen.queryByText('Each period')).not.toBeInTheDocument();
  });
});
