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

  const briefingRefreshes = () => invalidate.mock.calls.filter((call: unknown[]) => JSON.stringify(call[0]) === JSON.stringify({ queryKey: ['briefing'] })).length;

  it('reads the head, then refreshes the briefing and threads only when the ledger has moved on', async () => {
    const seen: number[] = []; // the refreshes already made when each poll was sent
    let calls = 0;
    vi.spyOn(client, 'get').mockImplementation(async () => {
      calls += 1;
      seen.push(briefingRefreshes());
      return { seq: calls <= 3 ? 5 : 6 }; // the head, twice nothing new, then something new
    });
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(calls).toBeGreaterThanOrEqual(5));
    expect(seen.slice(0, 4)).toEqual([0, 1, 1, 1]); // one refresh for the first read; none while the head stays at 5
    expect(seen[4]).toBe(2); // the head moved to 6: one more
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['thread'] });
  });

  it('asks only for the newest sequence number, never for events and their payloads (final review M7)', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue({ seq: 1 });
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(get.mock.calls.length).toBeGreaterThan(1));
    expect(new Set(get.mock.calls.map(([path]) => path))).toEqual(new Set(['/ledger/head']));
  });

  it('never stacks requests while one is slow', async () => {
    let inFlight = 0;
    let peak = 0;
    vi.spyOn(client, 'get').mockImplementation(async () => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 40));
      inFlight -= 1;
      return { seq: 1 };
    });
    renderHook(() => useLedgerHeartbeat({ intervalMs: 5 }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 200));
    expect(peak).toBe(1);
  });

  it('survives a failed poll without invalidating or giving up', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce({ seq: 1 });
    get.mockRejectedValueOnce(new Error('offline'));
    get.mockResolvedValue({ seq: 2 });
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(briefingRefreshes()).toBe(2));
    expect(get.mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it('stops when disabled or unmounted, and waits while the tab is hidden', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue({ seq: 0 });
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
          setTimeout(() => resolve({ seq: 1 }), 30);
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
      get.mockResolvedValueOnce({ seq: 1 }); // head
      get.mockRejectedValueOnce(new Error('x'));
      get.mockRejectedValueOnce(new Error('x'));
      get.mockResolvedValue({ seq: 1 });
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
      get.mockResolvedValueOnce({ seq: 1 });
      get.mockRejectedValueOnce(new ApiError(401, 'no session'));
      get.mockResolvedValue({ seq: 1 });
      renderHook(() => useLedgerHeartbeat({ intervalMs: 100 }), { wrapper: wrap(qc) });
      await vi.advanceTimersByTimeAsync(5000);
      expect(get).toHaveBeenCalledTimes(2);
    });

    it('polls at once when the tab becomes visible, without stacking', async () => {
      const get = vi.spyOn(client, 'get').mockResolvedValue({ seq: 1 });
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
