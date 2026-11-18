import { describe, expect, it } from 'vitest';
import type { Obligation } from '@/api/schema';
import { statusSort } from './Calendar';

const row = (id: string, status: string, due_date: string, days_late: number | null = null) => ({ id, status, due_date, days_late }) as unknown as Obligation;

describe('the outstanding requirements', () => {
  it('put the overdue first, the longest late at the top, then what is due, soonest first', () => {
    const rows = [
      row('due-later', 'due', '2026-11-30'),
      row('due-soon', 'due', '2026-11-20'),
      row('late-18', 'overdue', '2026-10-30', 18),
      row('late-40', 'overdue', '2026-10-08', 40),
      row('received', 'received', '2026-10-01'),
    ];
    const sorted = [...rows].sort((a, b) => statusSort(a).localeCompare(statusSort(b)));
    expect(sorted.map((entry) => entry.id)).toEqual(['late-40', 'late-18', 'due-soon', 'due-later', 'received']);
  });
});
