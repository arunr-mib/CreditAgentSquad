import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { SquadHome } from '../home/SquadHome';
import { Composer } from '../thread/Composer';

const status = vi.hoisted(() => ({ data: undefined as undefined | { model_connected: boolean; reason: string } }));
vi.mock('@/api/hooks', () => ({ useAgentsStatus: () => ({ data: status.data }) }));
vi.mock('../api/hooks', () => ({
  useAskCopilot: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useBriefing: () => ({ data: { as_of: '2026-11-20', needs_you: 0, items: [], overnight: [], open_clients: [], approvals: { offered: false, waiting: 0 }, oversight: { offered: false } }, isPending: false, error: null, refetch: vi.fn() }),
}));
vi.mock('../presence/Presence', () => ({ usePresence: () => ({ beginWork: () => () => {}, pulse: () => {}, say: () => {} }) }));

const OFF = { model_connected: false, reason: 'No model key is set for this deployment.' };

describe('Composer when the deployment has no model', () => {
  it.each([
    ['the client thread', { borrowerId: 'b1', borrowerName: 'Cindrel Tech' }, /Ask Squad about Cindrel Tech/],
    ['a case', { borrowerId: 'b1', workItemId: 'w1', label: 'Ask Squad about this case' }, /Ask Squad about this case/],
  ])('on %s says why in the server words and offers no Ask, before anyone types', (_where, props, name) => {
    status.data = OFF;
    render(<Composer {...props} />);
    expect(screen.getByText('No model key is set for this deployment.')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
  });

  it('on the home page says so too', async () => {
    status.data = OFF;
    const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: [] };
    const root = createRootRoute({ component: SquadHome });
    const client = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
    const router = createRouter({ routeTree: root.addChildren([client]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => true, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
          <RouterProvider router={router} />
        </AuthContext.Provider>
      </QueryClientProvider>,
    );
    expect(await screen.findByRole('textbox', { name: 'Ask Squad about the whole portfolio' })).toBeDisabled();
    expect(screen.getByText('No model key is set for this deployment.')).toBeInTheDocument();
  });

  it('is unchanged while the status loads or when the model is connected', () => {
    for (const data of [undefined, { model_connected: true, reason: '' }]) {
      status.data = data;
      const { unmount } = render(<Composer borrowerId={null} />);
      expect(screen.getByRole('textbox', { name: /whole portfolio/ })).toBeEnabled();
      expect(screen.getByText('Ctrl or Cmd + Enter to send')).toBeInTheDocument();
      unmount();
    }
  });
});
