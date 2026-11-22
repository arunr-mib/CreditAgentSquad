// Squad's two surfaces, and the legacy colour names the kept parts still read.
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AuthContext } from '@/auth/context';
import { ToastProvider, TooltipProvider } from '@/design';
import css from '../squad.css?raw';
import { contrast, legacyTokens, LOOKS, LOOK_IDS } from '../looks';
import { SquadShell } from '../shell/SquadShell';
import { surfaceOf } from '../shell/surface';

describe('surfaceOf', () => {
  it.each(['/', '/clients/QFL'])('%s is Squad\'s own conversation', (path) => expect(surfaceOf(path)).toBe('conversation'));
  it.each(['/approvals', '/portfolio', '/oversight', '/oversight/ledger', '/clients/QFL/file', '/clients/QFL/file/covenants', '/clients/QFL/file/packages', '/review-room', '/anything-else'])('%s is a Squad screen', (path) => expect(surfaceOf(path)).toBe('squad'));
});

function mountAt(path: string) {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404, text: async () => '{"detail":"Not found"}' }) as Response));
  const root = createRootRoute({ component: SquadShell });
  const routes = ['/', '/portfolio'].map((p) => createRoute({ getParentRoute: () => root, path: p, component: () => <p>screen {p}</p> }));
  const router = createRouter({ routeTree: root.addChildren(routes), history: createMemoryHistory({ initialEntries: [path] }) });
  const user = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: 't', role: 'analyst', permissions: ['view'] };
  const auth = { user, status: 'signed-in', can: () => true, signIn: vi.fn(), signOut: vi.fn(), retry: () => {} };
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={auth as never}>
        <TooltipProvider>
          <ToastProvider>
            <RouterProvider router={router as never} />
          </ToastProvider>
        </TooltipProvider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe('the shell by surface', () => {
  it('keeps the narrow column and the presence line on Squad\'s own routes', async () => {
    const { container } = mountAt('/');
    await screen.findByText('screen /');
    expect(container.querySelector('.sq-main')).toHaveAttribute('data-surface', 'conversation');
    expect(container.querySelector('.sq-presence')).not.toBeNull();
  });

  it('mounts My Portfolio as a Squad screen with the presence line', async () => {
    const { container } = mountAt('/portfolio');
    await screen.findByText('screen /portfolio');
    expect(container.querySelector('.sq-main')).toHaveAttribute('data-surface', 'squad');
    expect(container.querySelector('.sq-presence')).not.toBeNull();
  });

  it('caps the conversation at 860 px and a Squad screen at 1280 px', () => {
    expect(css).toMatch(/\.sq-main\s*\{[^}]*max-width:\s*860px/);
    expect(css).toMatch(/\.sq-main\[data-surface='squad'\]\s*\{[^}]*max-width:\s*1280px/);
    expect(css).not.toMatch(/data-surface='cockpit'/);
  });
});

describe('legacy cockpit tokens stay legible in every look', () => {
  // A legacy primary button is `bg-cobalt text-white`; inside Squad its text takes --sq-on-ink (see squad.css), so the pair is cobalt / onInk.
  it('squad.css sets the text of cobalt and amber-mark fills from the look, not white', () => {
    expect(css).toMatch(/\.sq-root \.bg-cobalt[^{]*\{[^}]*color:\s*var\(--sq-on-ink\)/);
    expect(css).toMatch(/\.sq-root \.bg-amber-mark[^{]*\{[^}]*color:\s*var\(--sq-on-ink\)/);
  });

  it.each(LOOK_IDS)('%s: every bridged legacy text and button pair is at least 4.5:1', (id) => {
    const t = legacyTokens(id);
    const v = LOOKS[id].vars;
    const pairs: Array<[string, string, string]> = [
      ['button text on --cobalt', v.onInk, t['--cobalt']!],
      ['button text on --cobalt-strong (hover)', v.onInk, t['--cobalt-strong']!],
      ['text on --amber-mark', v.onInk, t['--amber-mark']!],
      ['--ink-900 on --surface', t['--ink-900']!, t['--surface']!],
      ['--ink-900 on --canvas', t['--ink-900']!, t['--canvas']!],
      ['--ink-700 on --surface', t['--ink-700']!, t['--surface']!],
      ['--ink-500 on --canvas', t['--ink-500']!, t['--canvas']!],
      ['--cobalt (link) on --surface', t['--cobalt']!, t['--surface']!],
      ['--cobalt-strong on --cobalt-bg', t['--cobalt-strong']!, t['--cobalt-bg']!],
      ['--red on --red-bg', t['--red']!, t['--red-bg']!],
      ['--amber on --amber-bg', t['--amber']!, t['--amber-bg']!],
      ['--green on --green-bg', t['--green']!, t['--green-bg']!],
      ['--red on --surface', t['--red']!, t['--surface']!],
      ['--amber on --surface', t['--amber']!, t['--surface']!],
      ['--green on --surface', t['--green']!, t['--surface']!],
    ];
    for (const [name, fg, bg] of pairs) expect(contrast(fg, bg), `${id}: ${name}`).toBeGreaterThanOrEqual(4.5);
  });
});
