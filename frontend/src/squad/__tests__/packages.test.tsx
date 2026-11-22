import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '@/auth/context';
import { ToastProvider, TooltipProvider } from '@/design';
import { Packages } from '../clientfile/Packages';

const say = vi.fn();
vi.mock('../presence/Presence', () => ({ usePresence: () => ({ say }) }));
const PKG = { id: 'p1', title: 'Larkspur Environmental Services, Q3 2026', scope: 'borrower', status: 'generated', period_end: '2026-09-30', borrower_id: 'b1', borrower_name: 'Larkspur Environmental Services', released_at: null, released_by: null, files: [{ format: 'xlsx', name: 'larkspur-q3.xlsx', sha256: 'abc', size: 1000, borrower_id: 'b1', facts_used: 42 }], snapshot: { id: 'sn1', sha256: 'def', as_of: '2026-11-21T08:00:00Z', facts: 42, derived: 3 }, draft_commentary: [], can_release: true };
const BORROWER = { id: 'b1', code: 'LES', name: 'Larkspur Environmental Services' } as never;

function api(answers: Record<string, { status: number; body: unknown }>) {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${url.split('?')[0]}`;
    calls.push(key);
    const hit = answers[key] ?? { status: 200, body: [] };
    return { ok: hit.status < 400, status: hit.status, text: async () => JSON.stringify(hit.body) } as Response;
  }));
  return calls;
}

function mount(permissions: string[]) {
  const user = { id: 'u1', email: 'd@x', name: 'Dana Whitfield', title: '', role: 'portfolio_manager', permissions };
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={{ user, status: 'signed-in', can: (p: string) => permissions.includes(p), signIn: async () => user, signOut: async () => {}, retry: () => {} }}>
        <TooltipProvider><ToastProvider><Packages borrower={BORROWER} /></ToastProvider></TooltipProvider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => { vi.unstubAllGlobals(); say.mockClear(); });

describe('Packages in the client file', () => {
  it('lists a package with its files to download and verifies them on request', async () => {
    const calls = api({ 'GET /api/v1/packages': { status: 200, body: [PKG] }, 'POST /api/v1/packages/p1/verify': { status: 200, body: { ok: true, figures_checked: 42, snapshot_sha256: 'def', problems: [] } } });
    mount(['view', 'release_package', 'edit_commentary']);
    expect(await screen.findByRole('link', { name: /larkspur-q3\.xlsx/ })).toHaveAttribute('href', '/api/v1/packages/p1/files/larkspur-q3.xlsx');
    await userEvent.click(screen.getByRole('button', { name: 'Verify the files' }));
    expect(calls).toContain('POST /api/v1/packages/p1/verify');
  });

  it('shows the server’s refusal of a release in its own words', async () => {
    api({ 'GET /api/v1/packages': { status: 200, body: [PKG] }, 'POST /api/v1/packages/p1/release': { status: 409, body: { detail: 'This package did not pass verification: 1 figure(s) or file(s) do not resolve to the snapshot.' } } });
    mount(['view', 'release_package']);
    await userEvent.click(await screen.findByRole('button', { name: 'Release' }));
    expect(await screen.findByText(/did not pass verification/)).toBeInTheDocument();
  });

  it('tells a person without the served release permission that the server would refuse, naming no role', async () => {
    api({ 'GET /api/v1/packages': { status: 200, body: [PKG] } });
    const { container } = mount(['view', 'edit_commentary']);
    expect(await screen.findByText('Your role cannot release a package; the server would refuse it.')).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/portfolio manager|credit officer|credit analyst/i);
    expect(screen.queryByRole('button', { name: 'Release' })).not.toBeInTheDocument();
  });
});
