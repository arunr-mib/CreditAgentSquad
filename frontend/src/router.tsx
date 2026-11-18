import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Navigate, redirect, useRouterState } from '@tanstack/react-router';
import { useAuth } from '@/auth/context';
import { Button } from '@/design';
import { CommandCentre } from '@/screens/CommandCentre';
import { Notice } from '@/screens/parts';
import { SignIn } from '@/screens/SignIn';
import { WorkspaceDrawerProvider } from '@/drawer/context';
import { CopilotConversationProvider } from '@/drawer/CopilotPanel';
import { AppShell } from '@/shell/AppShell';
import { SourceProvider } from '@/source/SourceDrawer';

const str = (value: unknown): string | undefined => (typeof value === 'string' && value ? value : undefined);
const int = (value: unknown): number | undefined => {
  const parsed = typeof value === 'number' ? value : typeof value === 'string' ? Number.parseInt(value, 10) : Number.NaN;
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
};
/** Drops undefined keys so a search object never carries empty parameters into the address. */
function clean<T extends Record<string, unknown>>(search: T): T {
  return Object.fromEntries(Object.entries(search).filter(([, value]) => value !== undefined)) as T;
}

/** Signed out: only the sign-in screen. Signed in: the shell. A session that ends anywhere lands here. */
function Root() {
  const { status, retry } = useAuth();
  const location = useRouterState({ select: (state) => state.location });
  const atSignIn = location.pathname === '/sign-in';

  if (status === 'loading') {
    return (
      <div role="status" className="flex min-h-screen items-center justify-center text-body text-ink-500">
        Checking your session
      </div>
    );
  }
  if (status === 'unreachable' && !atSignIn) {
    return (
      <div className="mx-auto max-w-[560px] px-6 pt-24">
        <Notice tone="attention" title="The server could not be reached" action={<Button onClick={retry}>Try again</Button>}>
          The workspace reads everything from the API. Check that it is running, then try again.
        </Notice>
      </div>
    );
  }
  if (status === 'signed-out' || status === 'unreachable') {
    if (!atSignIn) return <Navigate to="/sign-in" search={location.pathname === '/' ? {} : { redirect: location.href }} replace />;
    return <SignIn />;
  }
  if (atSignIn) {
    const target = str((location.search as { redirect?: unknown }).redirect);
    return <Navigate to={target && target.startsWith('/') && !target.startsWith('//') ? target : '/command-centre'} replace />;
  }
  return (
    <SourceProvider>
      <WorkspaceDrawerProvider>
        <CopilotConversationProvider>
          <AppShell />
        </CopilotConversationProvider>
      </WorkspaceDrawerProvider>
    </SourceProvider>
  );
}

const rootRoute = createRootRoute({ component: Root });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/command-centre' });
  },
});

const signInRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sign-in',
  component: () => null,
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => clean({ redirect: str(search.redirect) }),
});

export const commandCentreRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/command-centre',
  component: CommandCentre,
  validateSearch: (search: Record<string, unknown>): { item?: string; severity?: string; type?: string } =>
    clean({ item: str(search.item), severity: str(search.severity), type: str(search.type) }),
});

const portfolioRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/portfolio',
  component: lazyRouteComponent(() => import('@/screens/Portfolio'), 'Portfolio'),
});

const borrowersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/borrowers',
  component: lazyRouteComponent(() => import('@/screens/Portfolio'), 'Borrowers'),
});

export const borrowerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/borrowers/$code',
  component: lazyRouteComponent(() => import('@/screens/borrower/BorrowerLayout'), 'BorrowerLayout'),
});

const borrowerChild = <TPath extends string>(path: TPath, load: () => Promise<Record<string, unknown>>, name: string) =>
  createRoute({ getParentRoute: () => borrowerRoute, path, component: lazyRouteComponent(load as () => Promise<Record<string, never>>, name) });

const summaryRoute = borrowerChild('/', () => import('@/screens/borrower/Summary'), 'Summary');
const loansRoute = borrowerChild('/loans', () => import('@/screens/borrower/Loans'), 'Loans');
const documentsRoute = borrowerChild('/documents', () => import('@/screens/borrower/Documents'), 'Documents');
export const documentRoute = createRoute({
  getParentRoute: () => borrowerRoute,
  path: '/documents/$documentId',
  component: lazyRouteComponent(() => import('@/screens/borrower/Documents'), 'DocumentViewer'),
  validateSearch: (search: Record<string, unknown>): { page?: number; fact?: string; quote?: string } =>
    clean({ page: int(search.page), fact: str(search.fact), quote: str(search.quote) }),
});
export const spreadsRoute = createRoute({
  getParentRoute: () => borrowerRoute,
  path: '/spreads',
  component: lazyRouteComponent(() => import('@/screens/borrower/Spreads'), 'Spreads'),
  validateSearch: (search: Record<string, unknown>): { periods?: string } => clean({ periods: str(search.periods) }),
});
export const covenantsRoute = createRoute({
  getParentRoute: () => borrowerRoute,
  path: '/covenants',
  component: lazyRouteComponent(() => import('@/screens/borrower/Covenants'), 'Covenants'),
  validateSearch: (search: Record<string, unknown>): { test?: string; period?: string } => clean({ test: str(search.test), period: str(search.period) }),
});
export const borrowingBaseRoute = createRoute({
  getParentRoute: () => borrowerRoute,
  path: '/borrowing-base',
  component: lazyRouteComponent(() => import('@/screens/borrower/BorrowingBase'), 'BorrowingBase'),
  validateSearch: (search: Record<string, unknown>): { review?: string } => clean({ review: str(search.review) }),
});
const signalsRoute = borrowerChild('/signals', () => import('@/screens/borrower/Signals'), 'Signals');
const reviewsRoute = borrowerChild('/reviews', () => import('@/screens/borrower/Reviews'), 'Reviews');
const packagesRoute = borrowerChild('/packages', () => import('@/screens/borrower/Packages'), 'Packages');
const timelineRoute = borrowerChild('/timeline', () => import('@/screens/borrower/Timeline'), 'Timeline');

const calendarRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/calendar',
  component: lazyRouteComponent(() => import('@/screens/Calendar'), 'Calendar'),
});
export const reviewRoomRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/review-room',
  component: lazyRouteComponent(() => import('@/screens/ReviewRoom'), 'ReviewRoom'),
  validateSearch: (search: Record<string, unknown>): { meeting?: string; sheet?: string } => clean({ meeting: str(search.meeting), sheet: str(search.sheet) }),
});
export const agentActivityRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/agent-activity',
  component: lazyRouteComponent(() => import('@/screens/AgentActivity'), 'AgentActivity'),
  validateSearch: (search: Record<string, unknown>): { run?: string } => clean({ run: str(search.run) }),
});
export const governanceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/governance',
  component: lazyRouteComponent(() => import('@/screens/Governance'), 'Governance'),
  validateSearch: (search: Record<string, unknown>): { tab?: string; entity?: string; action?: string } =>
    clean({ tab: str(search.tab), entity: str(search.entity), action: str(search.action) }),
});
const designRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/design',
  component: lazyRouteComponent(() => import('@/screens/DesignPage'), 'DesignPage'),
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  signInRoute,
  commandCentreRoute,
  portfolioRoute,
  borrowersRoute,
  borrowerRoute.addChildren([
    summaryRoute,
    loansRoute,
    documentsRoute,
    documentRoute,
    spreadsRoute,
    covenantsRoute,
    borrowingBaseRoute,
    signalsRoute,
    reviewsRoute,
    packagesRoute,
    timelineRoute,
  ]),
  calendarRoute,
  reviewRoomRoute,
  agentActivityRoute,
  governanceRoute,
  designRoute,
]);

export const router = createRouter({ routeTree, defaultPreload: 'intent', scrollRestoration: true });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
