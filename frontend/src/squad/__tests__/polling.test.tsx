import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as client from '@/api/client';
import { useLedgerHeartbeat } from '../api/polling';

const wrap = (qc: QueryClient) => ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;

describe('useLedgerHeartbeat', () => {
  let qc: QueryClient;
  let invalidate: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    qc = new QueryClient();
    invalidate = vi.spyOn(qc, 'invalidateQueries');
  });
  afterEach(() => vi.restoreAllMocks());

  it('reads the head once, then refreshes the briefing and threads when something new arrives', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce([{ seq: 5 }]); // the head
    get.mockResolvedValueOnce([]); // nothing new
    get.mockResolvedValue([{ seq: 6 }]); // something new
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 5, limit: 500 }, undefined));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['briefing'] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['thread'] });
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 6, limit: 500 }, undefined));
  });

  it('never stacks requests while one is slow', async () => {
    let inFlight = 0;
    let peak = 0;
    vi.spyOn(client, 'get').mockImplementation(async () => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 40));
      inFlight -= 1;
      return [];
    });
    renderHook(() => useLedgerHeartbeat({ intervalMs: 5 }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 200));
    expect(peak).toBe(1);
  });

  it('survives a failed poll without invalidating or giving up', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce([{ seq: 1 }]);
    get.mockRejectedValueOnce(new Error('offline'));
    get.mockResolvedValue([{ seq: 2 }]);
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['thread'] }));
    expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 1, limit: 500 }, undefined);
  });

  it('keeps paging from the new cursor when the ledger returns its 500-row cap', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce([{ seq: 10 }]); // head
    get.mockResolvedValueOnce(Array.from({ length: 500 }, (_, i) => ({ seq: 11 + i }))); // full page, ends at 510
    get.mockResolvedValue([]);
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 510, limit: 500 }, undefined));
  });

  it('stops when disabled or unmounted, and waits while the tab is hidden', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([]);
    const off = renderHook(() => useLedgerHeartbeat({ intervalMs: 5, enabled: false }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 40));
    expect(get).not.toHaveBeenCalled();
    off.unmount();
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    const hidden = renderHook(() => useLedgerHeartbeat({ intervalMs: 5 }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 40));
    expect(get.mock.calls.length).toBeLessThanOrEqual(1);
    hidden.unmount();
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
  });
});
