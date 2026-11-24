import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BorrowingBase } from '../clientfile/BorrowingBase';

const h = vi.hoisted(() => ({ open: vi.fn() }));
const line = (key: string, label: string, computed: string | null, certificate: string | null, difference: string | null, status: 'match' | 'mismatch' | null) => ({ line: key, label, depth: 0, computed, certificate, difference, status });
const REVIEWS = [
  { id: 'r2', period_end: '2026-09-30', outcome: 'mismatch', outcome_label: 'Certificate differs from the recalculation', loan_name: 'Revolver', calc_run_id: 'c2', availability_fact: null, work_item: { id: 'w1' },
    certificate_document: { id: 'd1', title: 'Borrowing base certificate, Q3', page_count: 2 },
    lines: [line('ar_eligible', 'Eligible receivables', '4100000', '4100000', null, 'match'), line('borrowing_base', 'Borrowing base', '5000000', '5200000', '-200000', 'mismatch'), line('reserves', 'Less: reserves', '10000', null, null, null)] },
  { id: 'r1', period_end: '2026-06-30', outcome: 'agrees', outcome_label: 'Agrees with the certificate', loan_name: 'Revolver', calc_run_id: 'c1', availability_fact: null, work_item: null, certificate_document: null, lines: [line('availability', 'Availability', '900000', '900000', null, 'match')] },
];
vi.mock('@/api/hooks', () => ({ useBorrowingBase: () => ({ data: REVIEWS, isPending: false, error: null }) }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: h.open, close: () => {}, current: null }) }));
vi.mock('@/source/figures', () => ({
  Absent: ({ reason }: { reason?: string }) => <span>{reason ?? 'Not measured'}</span>,
  FactFigure: () => null,
  SourcedFigure: ({ value, label }: { value: string; label: string }) => <span aria-label={label}>{value}</span>,
}));

describe('BorrowingBase: each line recalculated beside the certificate', () => {
  it('shows the latest review line by line with the difference only where the lines differ', () => {
    render(<BorrowingBase borrower={{ id: 'b1', code: 'QFL' } as never} />);
    const table = screen.getByRole('table', { name: /Borrowing base as of 30 Sep 2026/ });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(3);
    expect(within(rows[1]!).getByLabelText('Borrowing base, recalculated')).toHaveTextContent('5000000');
    expect(within(rows[1]!).getByLabelText('Borrowing base, on the certificate')).toHaveTextContent('5200000');
    expect(within(rows[1]!).getByLabelText('Borrowing base, recalculated less certificate')).toHaveTextContent('-200000');
    expect(within(rows[1]!).getByText('Differs')).toBeInTheDocument();
    expect(within(rows[0]!).getByText('Agrees')).toBeInTheDocument();
    expect(within(rows[0]!).getByText('No difference')).toBeInTheDocument();
    expect(within(rows[2]!).getByText('Not on the certificate')).toBeInTheDocument();
    expect(screen.getByText('Certificate differs from the recalculation')).toBeInTheDocument();
  });

  it('opens the certificate, and lets the person read an earlier review', async () => {
    render(<BorrowingBase borrower={{ id: 'b1', code: 'QFL' } as never} />);
    await userEvent.click(screen.getByRole('button', { name: 'The certificate' }));
    expect(h.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1' }));
    await userEvent.selectOptions(screen.getByLabelText('Review'), 'r1');
    expect(screen.getByRole('table', { name: /Borrowing base as of 30 Jun 2026/ })).toBeInTheDocument();
    expect(screen.getByText('Agrees with the certificate')).toBeInTheDocument();
  });
});
