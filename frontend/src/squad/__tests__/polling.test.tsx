import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { ApiError } from '@/api/client';
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
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 5, limit: 500 }, expect.anything()));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['briefing'] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['thread'] });
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 6, limit: 500 }, expect.anything()));
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
    expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 1, limit: 500 }, expect.anything());
  });

  it('keeps paging from the new cursor when the ledger returns its 500-row cap', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce([{ seq: 10 }]); // head
    get.mockResolvedValueOnce(Array.from({ length: 500 }, (_, i) => ({ seq: 11 + i }))); // full page, ends at 510
    get.mockResolvedValue([]);
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 510, limit: 500 }, expect.anything()));
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

  it('aborts a pending request on unmount and neither invalidates nor polls again', async () => {
    let signal: AbortSignal | undefined;
    const get = vi.spyOn(client, 'get').mockImplementation(
      (_p, _q, sig) =>
        new Promise((resolve) => {
          signal = sig;
          setTimeout(() => resolve([{ seq: 1 }]), 30);
        }) as never,
    );
    const view = renderHook(() => useLedgerHeartbeat({ intervalMs: 5 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(get).toHaveBeenCalledTimes(1));
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await new Promise((r) => setTimeout(r, 80));
    expect(get).toHaveBeenCalledTimes(1);
    expect(invalidate).not.toHaveBeenCalled();
  });

  describe('timing', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('backs off after failures and resets after a success', async () => {
      const get = vi.spyOn(client, 'get');
      get.mockResolvedValueOnce([{ seq: 1 }]); // head
      get.mockRejectedValueOnce(new Error('x'));
      get.mockRejectedValueOnce(new Error('x'));
      get.mockResolvedValue([]);
      renderHook(() => useLedgerHeartbeat({ intervalMs: 100 }), { wrapper: wrap(qc) });
      await vi.advanceTimersByTimeAsync(0);
      expect(get).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(100); // 1st poll fails
      expect(get).toHaveBeenCalledTimes(2);
      await vi.advanceTimersByTimeAsync(199); // next wait is 200
      expect(get).toHaveBeenCalledTimes(2);
      await vi.advanceTimersByTimeAsync(1); // 2nd poll fails
      expect(get).toHaveBeenCalledTimes(3);
      await vi.advanceTimersByTimeAsync(399); // next wait is 400
      expect(get).toHaveBeenCalledTimes(3);
      await vi.advanceTimersByTimeAsync(1); // succeeds
      expect(get).toHaveBeenCalledTimes(4);
      await vi.advanceTimersByTimeAsync(100); // back to the base interval
      expect(get).toHaveBeenCalledTimes(5);
    });

    it('stops for good on a 401', async () => {
      const get = vi.spyOn(client, 'get');
      get.mockResolvedValueOnce([{ seq: 1 }]);
      get.mockRejectedValueOnce(new ApiError(401, 'no session'));
      get.mockResolvedValue([]);
      renderHook(() => useLedgerHeartbeat({ intervalMs: 100 }), { wrapper: wrap(qc) });
      await vi.advanceTimersByTimeAsync(5000);
      expect(get).toHaveBeenCalledTimes(2);
    });

    it('polls at once when the tab becomes visible, without stacking', async () => {
      const get = vi.spyOn(client, 'get').mockResolvedValue([]);
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      renderHook(() => useLedgerHeartbeat({ intervalMs: 100000 }), { wrapper: wrap(qc) });
      await vi.advanceTimersByTimeAsync(0);
      expect(get).not.toHaveBeenCalled();
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
      document.dispatchEvent(new Event('visibilitychange'));
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(0);
      expect(get).toHaveBeenCalledTimes(1);
    });
  });
});
