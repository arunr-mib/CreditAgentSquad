import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Link, Navigate, redirect, useRouterState } from '@tanstack/react-router';
import { useAuth } from '@/auth/context';
import { Button } from '@/design';
import { Notice } from '@/screens/parts';
import { SignIn } from '@/screens/SignIn';
import { oldAddress } from '@/squad/redirects';
import { SquadShell } from '@/squad/shell/SquadShell';
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
    return <Navigate to={target && target.startsWith('/') && !target.startsWith('//') ? target : '/'} replace />;
  }
  return (
    <SourceProvider>
      <SquadShell />
    </SourceProvider>
  );
}

const rootRoute = createRootRoute({ component: Root });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: lazyRouteComponent(() => import('@/squad/home/SquadHome'), 'SquadHome'),
});

export const clientRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/clients/$code',
  component: lazyRouteComponent(() => import('@/squad/thread/ClientThread'), 'ClientThread'),
  validateSearch: (search: Record<string, unknown>): { case?: string } => clean({ case: str(search.case) }),
});

export const clientFileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/clients/$code/file',
  component: lazyRouteComponent(() => import('@/squad/clientfile/ClientFile'), 'ClientFile'),
});
export const clientFileViewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/clients/$code/file/$view',
  component: lazyRouteComponent(() => import('@/squad/clientfile/ClientFile'), 'ClientFile'),
  validateSearch: (search: Record<string, unknown>): { document?: string; page?: number; quote?: string; run?: string } =>
    clean({ document: str(search.document), page: int(search.page), quote: str(search.quote), run: str(search.run) }),
});

export const approvalsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/approvals',
  component: lazyRouteComponent(() => import('@/squad/approvals/Approvals'), 'Approvals'),
  validateSearch: (search: Record<string, unknown>): { case?: string } => clean({ case: str(search.case) }),
});

const signInRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sign-in',
  component: () => null,
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => clean({ redirect: str(search.redirect) }),
});

const portfolioRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/portfolio',
  component: lazyRouteComponent(() => import('@/squad/portfolio/Portfolio'), 'Portfolio'),
});

export const reviewRoomRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/review-room',
  component: lazyRouteComponent(() => import('@/squad/review/ReviewRoom'), 'ReviewRoom'),
  validateSearch: (search: Record<string, unknown>): { meeting?: string; sheet?: string } => clean({ meeting: str(search.meeting), sheet: str(search.sheet) }),
});
export const oversightRoute = createRoute({ getParentRoute: () => rootRoute, path: '/oversight', component: lazyRouteComponent(() => import('@/squad/oversight/Oversight'), 'Oversight') });
export const oversightTabRoute = createRoute({ getParentRoute: () => rootRoute, path: '/oversight/$tab', component: lazyRouteComponent(() => import('@/squad/oversight/Oversight'), 'Oversight') });
/** Every address the cockpit used lands on the Squad screen that replaced it (`oldAddress` is the one table). */
const toNew = async ({ location }: { location: { pathname: string; search: Record<string, unknown> } }) => {
  // Oversight is for some roles only: ask the server who this is, so an old address never lands on a refusal.
  let oversight = false;
  if (location.pathname === '/agent-activity' || location.pathname === '/governance') {
    try {
      const response = await fetch('/api/v1/me/briefing', { credentials: 'same-origin' });
      oversight = response.ok && Boolean(((await response.json()) as { oversight?: { offered?: boolean } }).oversight?.offered);
    } catch {
      oversight = false;
    }
  }
  const href = oldAddress(location.pathname, location.search, { oversight });
  if (href) throw redirect({ href, replace: true });
};
const old = (path: string) => createRoute({ getParentRoute: () => rootRoute, path, beforeLoad: toNew, component: () => null });
const oldRoutes = [
  '/borrowers', '/borrowers/$code', '/borrowers/$code/$view', '/borrowers/$code/documents/$documentId',
  '/command-centre', '/agent-activity', '/governance', '/calendar', '/design',
].map(old);

const routeTree = rootRoute.addChildren([
  indexRoute,
  clientRoute,
  clientFileRoute,
  clientFileViewRoute,
  approvalsRoute,
  signInRoute,
  portfolioRoute,
  reviewRoomRoute,
  oversightRoute,
  oversightTabRoute,
  ...oldRoutes,
]);

/** An address nothing answers: say so, and offer the way home (never the router's bare "Not Found"). */
function NotFound() {
  return (
    <div role="alert" className="sq-card">
      <p>There is no such page.</p>
      <Link to="/" className="sq-link">Back to Squad</Link>
    </div>
  );
}

export const router = createRouter({ routeTree, defaultPreload: 'intent', scrollRestoration: true, defaultNotFoundComponent: NotFound });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
