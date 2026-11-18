import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider, useRouterState } from '@tanstack/react-router';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState, type ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext, type AuthValue } from '@/auth/context';
import { DEMO_PASSWORD, DEMO_USERS } from '@/auth/demoUsers';
import { CommandPalette, ToastProvider, TooltipProvider } from '@/design';
import { WorkspaceDrawerContext, type WorkspaceDrawerValue } from '@/drawer/context';
import { useShellCommands } from '../commands';
import { Rail } from '../Rail';
import { RAIL_STORAGE_KEY, useRail } from '../useRail';
import { RUNS_POLL_MS } from '../useRunsInProgress';
import { UserMenu } from '../UserMenu';

const priya: ApiUser = {
  id: 'u-1',
  email: 'priya.raman@bankofstoic.example',
  name: 'Priya Raman',
  title: 'Senior Credit Analyst',
  role: 'analyst',
  permissions: ['view', 'decide_work_item'],
};

const portfolio = {
  work_items: {
    open: 13,
    by_type: [
      { item_type: 'covenant.breach', count: 4 },
      { item_type: 'bb.over_advance', count: 2 },
    ],
    by_severity: [
      { severity: 'critical', count: 4 },
      { severity: 'high', count: 8 },
    ],
  },
};
const borrowers = [
  {
    id: 'b-1',
    code: 'kestrel-bay-packaging',
    name: 'Kestrel Bay Packaging Corp.',
    industry: 'Manufacturing',
    analyst: 'Theo Lindqvist',
    relationship_manager: 'Dana Whitcombe',
  },
  { id: 'b-2', code: 'ashgrove-fleet', name: 'Ashgrove Fleet Maintenance, LLC', industry: 'Services', analyst: null, relationship_manager: null },
];

/** Answers the workspace's reads from fixed bodies, by path prefix. */
function mockApi(routes: Record<string, unknown>) {
  const calls: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url);
      const hit = Object.entries(routes).find(([path]) => url.startsWith(`/api/v1${path}`));
      return { ok: Boolean(hit), status: hit ? 200 : 404, text: async () => JSON.stringify(hit ? hit[1] : { detail: 'Not found' }) } as Response;
    }),
  );
  return calls;
}

/** A window of a given width, as far as media queries go. jsdom has no `matchMedia` of its own. */
function stubWindowWidth(width: number) {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: width >= Number(query.match(/min-width:\s*(\d+)px/)?.[1] ?? 0),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

const auth = (over: Partial<AuthValue> = {}): AuthValue => ({
  user: priya,
  status: 'signed-in',
  can: () => true,
  signIn: vi.fn(async () => priya),
  signOut: vi.fn(async () => {}),
  retry: () => {},
  ...over,
});

const drawer = (over: Partial<WorkspaceDrawerValue> = {}): WorkspaceDrawerValue => ({
  open: false,
  tab: 'item',
  itemId: null,
  borrowerCode: null,
  copilotScope: { kind: 'portfolio' },
  reasonDraft: null,
  openItem: () => {},
  openBorrower: () => {},
  openCopilot: () => {},
  setTab: () => {},
  setCopilotScope: () => {},
  draftReason: () => {},
  close: () => {},
  ...over,
});

/** Renders shell parts inside a router that knows the workspace's addresses, with the providers the shell sits in. */
function renderShell(ui: ReactNode, { at = '/command-centre', authValue = auth(), drawerValue = drawer() } = {}) {
  const rootRoute = createRootRoute({ component: () => <>{ui}</> });
  const paths = ['/command-centre', '/portfolio', '/borrowers', '/borrowers/$code', '/calendar', '/review-room', '/agent-activity', '/governance', '/design'];
  const routeTree = rootRoute.addChildren(paths.map((path) => createRoute({ getParentRoute: () => rootRoute, path, component: () => null })));
  const router = createRouter({ routeTree, history: createMemoryHistory({ initialEntries: [at] }) });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={authValue}>
        <WorkspaceDrawerContext.Provider value={drawerValue}>
          <TooltipProvider>
            <ToastProvider>
              {/* The test router stands in for the application's; its route table is not the registered one. */}
              <RouterProvider router={router as never} />
            </ToastProvider>
          </TooltipProvider>
        </WorkspaceDrawerContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return { router, ...view };
}

function RailHarness({ drawerOpen = false }: { drawerOpen?: boolean }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const rail = useRail(drawerOpen, pathname);
  return (
    <>
      <Rail pathname={pathname} rail={rail} />
      <input aria-label="Reason" />
    </>
  );
}

function PaletteHarness() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const commands = useShellCommands(pathname);
  const [open, setOpen] = useState(true);
  return <CommandPalette open={open} onOpenChange={setOpen} commands={commands} />;
}

const railState = async () => (await screen.findByRole('navigation', { name: 'Workspace' })).getAttribute('data-rail');

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe('navigation rail', () => {
  it('collapses and expands from its button, and remembers the choice in this browser', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/agent-runs': [] });
    const first = renderShell(<RailHarness />);
    expect(await railState()).toBe('expanded');
    expect(screen.getByRole('link', { name: /^Command centre/ })).toHaveAttribute('aria-current', 'page');

    await userEvent.click(screen.getByRole('button', { name: 'Collapse navigation' }));
    expect(await railState()).toBe('collapsed');
    expect(window.localStorage.getItem(RAIL_STORAGE_KEY)).toBe('collapsed');
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveAttribute('aria-expanded', 'false');

    // A new visit starts as the person left it.
    first.unmount();
    renderShell(<RailHarness />);
    expect(await railState()).toBe('collapsed');
    await userEvent.click(screen.getByRole('button', { name: 'Expand navigation' }));
    expect(await railState()).toBe('expanded');
    expect(window.localStorage.getItem(RAIL_STORAGE_KEY)).toBe('expanded');
  });

  it('switches on the [ key, but not while a text field has focus', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/agent-runs': [] });
    renderShell(<RailHarness />);
    expect(await railState()).toBe('expanded');

    await userEvent.keyboard('[[');
    expect(await railState()).toBe('collapsed');
    expect(window.localStorage.getItem(RAIL_STORAGE_KEY)).toBe('collapsed');

    const field = screen.getByRole('textbox', { name: 'Reason' });
    await userEvent.click(field);
    await userEvent.keyboard('[[');
    expect(field).toHaveValue('[');
    expect(await railState()).toBe('collapsed');
    expect(window.localStorage.getItem(RAIL_STORAGE_KEY)).toBe('collapsed');

    field.blur();
    await userEvent.keyboard('[[');
    expect(await railState()).toBe('expanded');
  });

  it('keeps the page its room on a narrower window: the labels open over the page and go away again', async () => {
    stubWindowWidth(1024);
    window.localStorage.setItem(RAIL_STORAGE_KEY, 'expanded');
    mockApi({ '/ui/portfolio': portfolio, '/agent-runs': [] });
    renderShell(<RailHarness />);
    const nav = await screen.findByRole('navigation', { name: 'Workspace' });
    // Beside the page the rail is icons, whatever was chosen on a wider window.
    expect(nav).toHaveAttribute('data-rail', 'collapsed');

    await userEvent.click(screen.getByRole('button', { name: 'Expand navigation' }));
    expect(nav).toHaveAttribute('data-rail', 'expanded');
    expect(nav).toHaveAttribute('data-floating', 'true');
    await userEvent.keyboard('{Escape}');
    expect(nav).toHaveAttribute('data-rail', 'collapsed');
    expect(nav).not.toHaveAttribute('data-floating');

    await userEvent.keyboard('[[');
    expect(nav).toHaveAttribute('data-floating', 'true');
    await userEvent.click(screen.getByRole('textbox', { name: 'Reason' }));
    expect(nav).toHaveAttribute('data-rail', 'collapsed');

    await userEvent.keyboard('{Tab}');
    await userEvent.click(screen.getByRole('button', { name: 'Expand navigation' }));
    await userEvent.click(screen.getByRole('link', { name: 'Portfolio' }));
    await waitFor(() => expect(screen.getByRole('link', { name: 'Portfolio' })).toHaveAttribute('aria-current', 'page'));
    expect(nav).toHaveAttribute('data-rail', 'collapsed');
    // None of this is a choice to remember.
    expect(window.localStorage.getItem(RAIL_STORAGE_KEY)).toBe('expanded');
  });

  it('stays collapsed beside the page while the drawer is open on a window narrower than 1400 px, whatever the choice', async () => {
    stubWindowWidth(1280);
    window.localStorage.setItem(RAIL_STORAGE_KEY, 'expanded');
    mockApi({ '/ui/portfolio': portfolio, '/agent-runs': [] });
    const view = renderShell(<RailHarness drawerOpen />);
    expect(await railState()).toBe('collapsed');
    await userEvent.click(screen.getByRole('button', { name: 'Expand navigation' }));
    expect(screen.getByRole('navigation', { name: 'Workspace' })).toHaveAttribute('data-floating', 'true');
    expect(window.localStorage.getItem(RAIL_STORAGE_KEY)).toBe('expanded');

    // Without the drawer the same window has room, and the choice stands.
    view.unmount();
    const closed = renderShell(<RailHarness />);
    expect(await railState()).toBe('expanded');
    expect(screen.getByRole('navigation', { name: 'Workspace' })).not.toHaveAttribute('data-floating');

    // On a wide window the rail and the drawer both fit.
    closed.unmount();
    stubWindowWidth(1440);
    renderShell(<RailHarness drawerOpen />);
    expect(await railState()).toBe('expanded');
    expect(screen.getByRole('navigation', { name: 'Workspace' })).not.toHaveAttribute('data-floating');
  });

  it('shows the open-item count the API reports, and a still mark while an agent run is in progress', async () => {
    mockApi({
      '/ui/portfolio': portfolio,
      '/agent-runs': [
        { id: 'r-1', status: 'running' },
        { id: 'r-2', status: 'completed' },
      ],
    });
    renderShell(<RailHarness />);
    expect(await screen.findByRole('link', { name: 'Command centre, 13 open items' })).toBeInTheDocument();
    const mark = await screen.findByRole('img', { name: '1 agent run in progress' });
    expect(within(screen.getByRole('link', { name: 'Agent activity, 1 agent run in progress' })).getByRole('img')).toBe(mark);
    expect(mark.className).not.toMatch(/animate|pulse/);
    expect(RUNS_POLL_MS).toBeGreaterThanOrEqual(20_000);
  });

  it('reads each link’s visible words at the start of its accessible name (WCAG 2.5.3, label in name)', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/agent-runs': [] });
    renderShell(<RailHarness />);
    const queue = await screen.findByRole('link', { name: 'Command centre, 13 open items' });
    const home = screen.getByRole('link', { name: /, home$/ });
    // What a sighted person sees, as a screen reader joins it: the words must not run together.
    const words = (element: HTMLElement) => (element.textContent ?? '').replace(/\s+/g, ' ').trim().toLowerCase();
    const name = (element: HTMLElement) => (element.getAttribute('aria-label') ?? '').replace(/[,.]/g, '').toLowerCase();
    expect(words(home)).toBe('credit agent squad bank of stoic');
    expect(name(home).startsWith(words(home))).toBe(true);
    expect(words(queue)).toBe('command centre 13');
    expect(name(queue).startsWith(words(queue))).toBe(true);
  });

  it('shows no mark when no run is in progress', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/agent-runs': [{ id: 'r-2', status: 'completed' }] });
    renderShell(<RailHarness />);
    await screen.findByRole('link', { name: 'Command centre, 13 open items' });
    expect(screen.queryByRole('img', { name: /in progress/ })).toBeNull();
  });
});

describe('user menu', () => {
  it('names the person and the role in plain text', async () => {
    renderShell(<UserMenu demoUsers={DEMO_USERS} />);
    const trigger = await screen.findByRole('button', { name: /Account menu/ });
    expect(within(trigger).getByText('Priya Raman', { selector: '[data-user-name]' })).toBeInTheDocument();
    expect(within(trigger).getByText('Credit analyst', { selector: '[data-user-role]' })).toBeInTheDocument();
  });

  it('switches demo user by signing out, then signing in as the chosen person', async () => {
    const dana: ApiUser = {
      id: 'u-3',
      email: 'dana.whitfield@bankofstoic.example',
      name: 'Dana Whitfield',
      title: 'Portfolio Manager',
      role: 'portfolio_manager',
      permissions: ['view'],
    };
    const signOut = vi.fn(async () => {});
    const signIn = vi.fn(async () => dana);
    renderShell(<UserMenu demoUsers={DEMO_USERS} />, { authValue: auth({ signIn, signOut }) });

    await userEvent.click(await screen.findByRole('button', { name: /Account menu/ }));
    const menu = await screen.findByRole('menu');
    expect(within(menu).getByText('Switch demo user')).toBeInTheDocument();
    // Everyone but the person already signed in, each with a role.
    // ... then the design system (out of the phone's bottom bar) and signing out.
    expect(within(menu).getAllByRole('menuitem')).toHaveLength(DEMO_USERS.length - 1 + 2);
    expect(within(menu).getByRole('menuitem', { name: 'Design system' })).toHaveAttribute('href', '/design');
    expect(within(menu).queryByRole('menuitem', { name: /Priya Raman/ })).toBeNull();
    await userEvent.click(within(menu).getByRole('menuitem', { name: /^Dana Whitfield\s*Portfolio manager$/ }));

    await waitFor(() => expect(signIn).toHaveBeenCalledTimes(1));
    expect(signOut).toHaveBeenCalledTimes(1);
    expect(signIn).toHaveBeenCalledWith('dana.whitfield@bankofstoic.example', DEMO_PASSWORD);
    expect(signOut.mock.invocationCallOrder[0]).toBeLessThan(signIn.mock.invocationCallOrder[0] ?? 0);
    expect(await screen.findByText('Signed in as Dana Whitfield')).toBeInTheDocument();
  });

  it('says so when the sign-in as another person fails', async () => {
    const signIn = vi.fn(async () => {
      throw new Error('Email or password is wrong.');
    });
    renderShell(<UserMenu demoUsers={DEMO_USERS} />, { authValue: auth({ signIn }) });
    await userEvent.click(await screen.findByRole('button', { name: /Account menu/ }));
    await userEvent.click(await screen.findByRole('menuitem', { name: /Helen Strand/ }));
    expect(await screen.findByText('Could not sign in as Helen Strand')).toBeInTheDocument();
  });

  it('offers no demo users where they are switched off, and still signs out', async () => {
    const signOut = vi.fn(async () => {});
    renderShell(<UserMenu demoUsers={[]} />, { authValue: auth({ signOut }) });
    await userEvent.click(await screen.findByRole('button', { name: /Account menu/ }));
    const menu = await screen.findByRole('menu');
    expect(within(menu).queryByText('Switch demo user')).toBeNull();
    expect(within(menu).getAllByRole('menuitem').map((item) => item.textContent)).toEqual(['Design system', 'Sign out']);
    await userEvent.click(within(menu).getByRole('menuitem', { name: 'Sign out' }));
    expect(signOut).toHaveBeenCalledTimes(1);
  });
});

describe('command palette commands', () => {
  it('lists the Copilot commands and opens the Copilot scoped to the portfolio or to the borrower on screen', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/borrowers': borrowers });
    const openCopilot = vi.fn();
    renderShell(<PaletteHarness />, { at: '/borrowers/kestrel-bay-packaging', drawerValue: drawer({ openCopilot }) });

    const copilot = await screen.findByRole('group', { name: 'Copilot' });
    expect(within(copilot).getByRole('option', { name: /Ask Copilot about the portfolio/ })).toBeInTheDocument();
    await userEvent.click(await within(copilot).findByRole('option', { name: /Ask Copilot about Kestrel Bay Packaging Corp\./ }));
    expect(openCopilot).toHaveBeenCalledWith({ kind: 'borrower', code: 'kestrel-bay-packaging' });
    expect(screen.queryByRole('combobox')).toBeNull();
  });

  it('asks about the portfolio from any other screen', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/borrowers': borrowers });
    const openCopilot = vi.fn();
    renderShell(<PaletteHarness />, { drawerValue: drawer({ openCopilot }) });
    const input = await screen.findByRole('combobox', { name: 'Search' });
    expect(screen.queryByRole('option', { name: /Ask Copilot about Kestrel/ })).toBeNull();
    await userEvent.type(input, 'copilot portfolio');
    await userEvent.keyboard('{Enter}');
    expect(openCopilot).toHaveBeenCalledWith({ kind: 'portfolio' });
  });

  it('groups borrowers, screens and queue filters, and a queue filter opens the command centre with the filter in the address', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/borrowers': borrowers });
    const { router } = renderShell(<PaletteHarness />, { at: '/portfolio' });
    await screen.findByRole('option', { name: /Kestrel Bay Packaging Corp\./ });
    expect(screen.getAllByRole('group').map((group) => group.getAttribute('aria-label'))).toEqual(['Copilot', 'Queue', 'Go to', 'Borrowers']);
    // The counts beside the filters are the API's.
    expect(screen.getByRole('option', { name: /Show critical exceptions\s*4 open/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Show exceptions my role can decide\s*Credit analyst/ })).toBeInTheDocument();
    // The long tail of filters is listed once the person types.
    expect(screen.queryByRole('option', { name: /Show borrowing base exceptions/ })).toBeNull();

    await userEvent.type(screen.getByRole('combobox', { name: 'Search' }), 'borrowing base');
    await userEvent.click(screen.getByRole('option', { name: /Show borrowing base exceptions\s*2 open/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/command-centre'));
    expect(router.state.location.search).toEqual({ type: 'borrowing_base' });
  });

  it('sends "my role can decide" and "critical" as the search parameters the queue reads', async () => {
    mockApi({ '/ui/portfolio': portfolio, '/borrowers': borrowers });
    const first = renderShell(<PaletteHarness />, { at: '/portfolio' });
    await userEvent.click(await screen.findByRole('option', { name: /Show exceptions my role can decide/ }));
    await waitFor(() => expect(first.router.state.location.search).toEqual({ type: 'mine' }));
    first.unmount();

    const second = renderShell(<PaletteHarness />, { at: '/portfolio' });
    await userEvent.click(await screen.findByRole('option', { name: /Show critical exceptions/ }));
    await waitFor(() => expect(second.router.state.location.search).toEqual({ severity: 'critical' }));
    expect(second.router.state.location.pathname).toBe('/command-centre');
  });
});
