import { createRootRoute, createRoute, createRouter, lazyRouteComponent, redirect } from '@tanstack/react-router';
import { Placeholder } from '@/screens/Placeholder';
import { CommandCentre } from '@/screens/showcase/CommandCentre';
import { AppShell } from '@/shell/AppShell';
import { NAV } from '@/shell/nav';

const rootRoute = createRootRoute({ component: AppShell });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/showcase/command-centre' });
  },
});

const commandCentreRoute = createRoute({ getParentRoute: () => rootRoute, path: '/showcase/command-centre', component: CommandCentre });
const covenantsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/showcase/covenants',
  component: lazyRouteComponent(() => import('@/screens/showcase/CovenantWorkspace'), 'CovenantWorkspace'),
});
const spreadRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/showcase/spread',
  component: lazyRouteComponent(() => import('@/screens/showcase/SpreadGrid'), 'SpreadGrid'),
  validateSearch: (search: Record<string, unknown>): { cell?: string } => (typeof search.cell === 'string' ? { cell: search.cell } : {}),
});
const designRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/design',
  component: lazyRouteComponent(() => import('@/screens/DesignPage'), 'DesignPage'),
});

function placeholder<TPath extends string>(path: TPath) {
  const item = NAV.find((entry) => entry.to === path);
  return createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => <Placeholder title={item?.label ?? 'Not built yet'} description={item?.description ?? 'This screen'} />,
  });
}

const portfolioRoute = placeholder('/portfolio');
const calendarRoute = placeholder('/calendar');
const reviewRoomRoute = placeholder('/review-room');
const agentActivityRoute = placeholder('/agent-activity');
const governanceRoute = placeholder('/governance');

const routeTree = rootRoute.addChildren([
  indexRoute,
  commandCentreRoute,
  covenantsRoute,
  spreadRoute,
  designRoute,
  portfolioRoute,
  calendarRoute,
  reviewRoomRoute,
  agentActivityRoute,
  governanceRoute,
]);

export const router = createRouter({ routeTree, defaultPreload: 'intent', scrollRestoration: true });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
