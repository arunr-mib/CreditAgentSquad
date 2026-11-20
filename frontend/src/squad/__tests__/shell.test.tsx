// frontend/src/squad/__tests__/shell.test.tsx
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { buildCommands } from '../shell/commands';
import { clientFile, threadHref } from '../links';
import { SquadNav } from '../shell/SquadNav';

const clients = [{ code: 'QFL', name: 'Quillfeather Labs, Inc.' }, { code: 'ZZZ', name: 'Zephyr Zinc Works, Inc.' }];

function mountNav(props: Partial<Parameters<typeof SquadNav>[0]> = {}) {
  const root = createRootRoute({
    component: () => (
      <SquadNav collapsed={false} onToggle={() => {}} needs={2} openClients={[{ borrower_id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', open: 2 }]}
        pathname="/" userName="Priya Raman" onSignOut={() => {}} {...{ role: 'analyst', ...props }} />
    ),
  });
  const routes = ['/', '/portfolio', '/clients/$code', '/governance', '/agent-activity'].map((path) => createRoute({ getParentRoute: () => root, path, component: () => null }));
  const router = createRouter({ routeTree: root.addChildren(routes), history: createMemoryHistory({ initialEntries: ['/'] }) });
  return render(<RouterProvider router={router} />);
}

describe('SquadNav', () => {
  it('has the Squad row with its needs-you count, My Portfolio, and only clients with something open', async () => {
    mountNav();
    const home = await screen.findByRole('link', { name: /squad.*2 need you/i });
    expect(home).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /my portfolio/i })).toHaveAttribute('href', '/portfolio');
    const cases = screen.getByRole('navigation', { name: /open cases/i });
    expect(within(cases).getAllByRole('link')).toHaveLength(1);
    expect(within(cases).getByRole('link', { name: /quillfeather/i })).toHaveAttribute('href', '/clients/QFL');
  });

  it('shows no needs-you count when nothing needs her, and no Open cases list when nothing is open', async () => {
    mountNav({ needs: 0, openClients: [] });
    expect(await screen.findByRole('link', { name: /^squad$/i })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /open cases/i })).not.toBeInTheDocument();
  });

  it('collapses and expands from one button that says which', async () => {
    const onToggle = vi.fn();
    mountNav({ collapsed: true, onToggle });
    const toggle = await screen.findByRole('button', { name: /expand navigation/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(onToggle).toHaveBeenCalled();
  });

  it('lists oversight only for the roles that have it', async () => {
    const { unmount } = mountNav({ role: 'analyst' });
    await screen.findByRole('link', { name: /my portfolio/i });
    expect(screen.queryByRole('link', { name: /oversight|agent activity/i })).not.toBeInTheDocument();
    unmount();
    mountNav({ role: 'admin' });
    expect(await screen.findByRole('link', { name: /agent activity/i })).toBeInTheDocument();
  });
});

describe('palette commands', () => {
  const run = vi.fn();
  beforeEach(() => run.mockClear());

  it('offers navigation, every client by name (search only), and the five looks', () => {
    const commands = buildCommands({ clients, go: run, setLook: run, role: 'analyst' });
    expect(commands.filter((c) => c.group === 'Look')).toHaveLength(5);
    const client = commands.find((c) => c.label === 'Quillfeather Labs, Inc.')!;
    expect(client.searchOnly).toBe(true);
    client.run();
    expect(run).toHaveBeenCalledWith('/clients/QFL');
    expect(commands.find((c) => c.label === 'My Portfolio')).toBeTruthy();
    expect(commands.find((c) => c.label === 'Squad')).toBeTruthy();
  });

  it('hides oversight commands from roles without it', () => {
    expect(buildCommands({ clients, go: run, setLook: run, role: 'analyst' }).some((c) => c.group === 'Oversight')).toBe(false);
    expect(buildCommands({ clients, go: run, setLook: run, role: 'credit_review' }).some((c) => c.group === 'Oversight')).toBe(true);
  });
});

describe('links', () => {
  it('addresses a thread and a case in one place', () => {
    expect(threadHref('QFL', 'abc')).toEqual({ to: '/clients/$code', params: { code: 'QFL' }, search: { case: 'abc' } });
    expect(threadHref('QFL')).toEqual({ to: '/clients/$code', params: { code: 'QFL' }, search: {} });
    expect(clientFile('QFL', 'covenants')).toBe('/borrowers/QFL/covenants');
  });
});
