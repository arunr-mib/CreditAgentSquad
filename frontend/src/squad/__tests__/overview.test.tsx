import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type * as ApiHooks from '../api/hooks';
import type { TrackRecordRow } from '../api/types';
import { Overview } from '../clientfile/views';

const track: TrackRecordRow[] = [
  { task: 'read_certificate', agent_name: 'certificate_reader', agent_label: 'Certificate reader agent', task_label: 'Read certificate', right: 6, corrected: 1, unreviewed: 3, checked: 10, since: '2026-10-03T09:00:00Z', last_correction_at: '2026-11-02T10:00:00Z' },
  { task: 'read_statements', agent_name: 'spreading', agent_label: 'Spreading agent', task_label: 'Read statements', right: 4, corrected: 0, unreviewed: 0, checked: 4, since: '2026-10-05T09:00:00Z', last_correction_at: null },
];
const lessons = [
  { id: 'l1', topic: 'line_mapping', tag: 'map_to_arr', text: 'Recurring revenue here is ARR.', by: 'Priya Raman', at: '2026-11-01T10:00:00Z', work_item_id: null },
  { id: 'l2', topic: 'line_mapping', tag: null, text: 'Ignore the pro forma column.', by: 'Tomas Keller', at: '2026-11-03T10:00:00Z', work_item_id: null },
];
const ok = (data: unknown) => ({ data, isPending: false, error: null });
vi.mock('@/api/hooks', () => ({
  useBorrowerOverview: () => ok({ exposure: {}, cycle: null }),
  useSignals: () => ok([]),
  useActions: () => ok([]), useBorrowerCovenants: () => ok([]), useBorrowerTerms: () => ok(null), useBorrowingBase: () => ok(null),
  useDocuments: () => ok([]), useFactsById: () => ok({}), useSpread: () => ok(null),
}));
vi.mock('../api/hooks', async () => ({
  ...(await vi.importActual<typeof ApiHooks>('../api/hooks')),
  useMeasure: () => ok({ kind: 'rml', label: 'Runway (months)', points: [] }),
  useTrackRecord: () => ok(track), useLessons: () => ok(lessons),
}));
vi.mock('@/source/figures', () => ({ FactFigure: () => null, Absent: () => <span>Not measured</span>, SourcedFigure: () => null }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: () => {}, close: () => {}, current: null }) }));
vi.mock('@/squad/clientfile/RunStage', () => ({ RunStage: () => null }));
vi.mock('@/squad/clientfile/UploadDocument', () => ({ UploadDocument: () => null }));
vi.mock('@/squad/clientfile/review/Commentary', () => ({ Commentary: () => null }));

const borrower = { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', template_id: 'vc-1' } as never;
const mount = () => render(<QueryClientProvider client={new QueryClient()}><Overview borrower={borrower} /></QueryClientProvider>);

describe('Overview: track record and what Squad remembers', () => {
  it('shows the server\u2019s counts so that Checked is exactly Right + Corrected + Not yet reviewed', () => {
    mount();
    const table = within(screen.getByRole('region', { name: 'Track record' })).getByRole('table');
    expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Task', 'Checked', 'Right', 'Corrected', 'Not yet reviewed', 'Last correction']);
    const [first, second] = within(table).getAllByRole('row').slice(1);
    expect(within(first!).getAllByRole('cell').map((c) => c.textContent)).toEqual(['10', '6', '1', '3', expect.stringMatching(/2 Nov 2026/)]);
    expect(within(second!).getAllByRole('cell').map((c) => c.textContent)).toEqual(['4', '4', '0', '0', 'None']);
  });

  it('names the agent in the served words, never the stored id, and says since when', () => {
    mount();
    const table = within(screen.getByRole('region', { name: 'Track record' })).getByRole('table');
    expect(within(table).getByRole('rowheader', { name: /Certificate reader agent \u00b7 Read certificate/ })).toBeInTheDocument();
    expect(table.textContent).not.toMatch(/_/);
    expect(within(table).getByText(/since 3 Oct 2026/)).toBeInTheDocument();
  });

  it('lists what Squad remembers with who taught it', () => {
    mount();
    const list = within(screen.getByRole('region', { name: 'What Squad remembers' })).getByRole('list');
    expect(within(list).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      expect.stringContaining('Recurring revenue here is ARR.'), expect.stringContaining('Ignore the pro forma column.'),
    ]);
    expect(within(list).getByText(/Priya Raman/)).toBeInTheDocument();
  });
});
