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
      <SquadNav collapsed={false} onToggle={() => {}} needs={2} showApprovals={false} openClients={[{ borrower_id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', open: 2 }]}
        pathname="/" userName="Priya Raman" onSignOut={() => {}} {...{ oversight: false, ...props }} />
    ),
  });
  const routes = ['/', '/portfolio', '/approvals', '/review-room', '/clients/$code', '/oversight'].map((path) => createRoute({ getParentRoute: () => root, path, component: () => null }));
  const router = createRouter({ routeTree: root.addChildren(routes), history: createMemoryHistory({ initialEntries: ['/'] }) });
  return render(<RouterProvider router={router} />);
}

describe('SquadNav', () => {
  it('shows an Approvals link only when the server says it is offered', async () => {
    const { unmount } = mountNav({ showApprovals: true });
    expect(await screen.findByRole('link', { name: 'Approvals' })).toHaveAttribute('href', '/approvals');
    unmount();
    mountNav({ showApprovals: false });
    await screen.findByRole('link', { name: /My Portfolio/ });
    expect(screen.queryByRole('link', { name: 'Approvals' })).not.toBeInTheDocument();
  });

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

  it('links the review room for every person, whatever the server offers', async () => {
    mountNav({ showApprovals: false, oversight: false });
    expect(await screen.findByRole('link', { name: 'Review room' })).toHaveAttribute('href', '/review-room');
  });

  it('lists oversight only for the roles that have it', async () => {
    const { unmount } = mountNav({ oversight: false });
    await screen.findByRole('link', { name: /my portfolio/i });
    expect(screen.queryByRole('link', { name: /oversight/i })).not.toBeInTheDocument();
    unmount();
    mountNav({ oversight: true });
    expect(await screen.findByRole('link', { name: 'Oversight' })).toHaveAttribute('href', '/oversight');
  });
});

describe('palette commands', () => {
  const run = vi.fn();
  beforeEach(() => run.mockClear());

  it('offers navigation, every client by name (search only), and the five looks', () => {
    const commands = buildCommands({ clients, go: run, setLook: run, oversight: false, approvals: false });
    expect(commands.filter((c) => c.group === 'Look')).toHaveLength(5);
    const client = commands.find((c) => c.label === 'Quillfeather Labs, Inc.')!;
    expect(client.searchOnly).toBe(true);
    client.run();
    expect(run).toHaveBeenCalledWith('/clients/QFL');
    expect(commands.find((c) => c.label === 'My Portfolio')).toBeTruthy();
    expect(commands.find((c) => c.label === 'Squad')).toBeTruthy();
  });

  it('offers the review room to everyone', () => {
    const c = buildCommands({ clients, go: run, setLook: run, oversight: false, approvals: false }).find((x) => x.label === 'Review room')!;
    c.run();
    expect(run).toHaveBeenCalledWith('/review-room');
  });

  it('hides oversight commands from roles without it', () => {
    expect(buildCommands({ clients, go: run, setLook: run, oversight: false, approvals: false }).some((c) => c.group === 'Oversight')).toBe(false);
    expect(buildCommands({ clients, go: run, setLook: run, oversight: true, approvals: false }).some((c) => c.group === 'Oversight')).toBe(true);
  });
});

describe('palette: oversight', () => {
  it('a search for ledger finds the ledger, not Oversight, first', () => {
    const commands = buildCommands({ clients, go: vi.fn(), setLook: vi.fn(), oversight: true, approvals: false });
    const mentions = commands.filter((c) => `${c.label} ${c.hint ?? ''}`.toLowerCase().includes('ledger'));
    expect(mentions.map((c) => c.id)).toEqual(['go-ledger']);
  });
});

describe('links', () => {
  it('addresses a thread and a case in one place', () => {
    expect(threadHref('QFL', 'abc')).toEqual({ to: '/clients/$code', params: { code: 'QFL' }, search: { case: 'abc' } });
    expect(threadHref('QFL')).toEqual({ to: '/clients/$code', params: { code: 'QFL' }, search: {} });
    expect(clientFile('QFL', 'covenants')).toBe('/clients/QFL/file/covenants');
  });
});

describe('collapsed nav', () => {
  it('names every link when collapsed', async () => {
    mountNav({ collapsed: true, oversight: true });
    const home = await screen.findByRole('link', { name: /squad.*2 need you/i });
    expect(home).toHaveAttribute('title', 'Squad');
    for (const name of [/my portfolio/i, /oversight/i]) {
      expect(screen.getByRole('link', { name })).toBeInTheDocument();
    }
    for (const link of screen.getAllByRole('link')) expect(link).toHaveAccessibleName();
  });

  it('shows one Open cases button when collapsed, not a circle per client, and expands to the names', async () => {
    const toggle = vi.fn();
    mountNav({ collapsed: true, onToggle: toggle });
    expect(await screen.findByRole('link', { name: /squad/i })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /open cases/i })).not.toBeInTheDocument();
    expect(document.querySelectorAll('.sq-initial')).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: 'Clients with open cases: 1' }));
    expect(toggle).toHaveBeenCalled();
  });

  it('shows the product name when expanded', async () => {
    mountNav();
    expect(await screen.findByText('Credit Squad')).toBeInTheDocument();
  });
});
