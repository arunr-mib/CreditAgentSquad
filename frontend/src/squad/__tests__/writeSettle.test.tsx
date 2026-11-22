import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, act } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import { useDecideCase, useSendDraft } from '../api/hooks';

vi.mock('@/api/client', async (orig) => {
  const real = await orig<Record<string, unknown>>();
  const Err = real.ApiError as typeof ApiError;
  return { ...real, post: vi.fn().mockRejectedValue(new Err(422, 'already sent')) };
});

describe('squad writes', () => {
  it('refetch the thread and briefing even when the write is refused', async () => {
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
    const { result } = renderHook(() => useSendDraft(), { wrapper });
    await act(async () => { await result.current.mutateAsync({ draft_id: 'd1' }).catch((e) => expect(e).toBeInstanceOf(ApiError)); });
    const keys = spy.mock.calls.map((c) => JSON.stringify(c[0]?.queryKey));
    expect(keys).toContain('["thread"]');
    expect(keys).toContain('["briefing"]');
  });

  it('a decision on a case refetches what a decision changes: the sheet, the queue, the ledger and the case', async () => {
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
    const { result } = renderHook(() => useDecideCase('w1'), { wrapper });
    await act(async () => { await result.current.mutateAsync({ decision: 'approve', reason: '' }).catch(() => {}); });
    const keys = spy.mock.calls.map((c) => JSON.stringify(c[0]?.queryKey));
    for (const key of ['case', 'approvals', 'review-sheet', 'review-sheets', 'work-items', 'ledger']) expect(keys, key).toContain(`["${key}"]`);
  });
});
