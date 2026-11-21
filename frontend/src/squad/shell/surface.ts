// frontend/src/squad/shell/surface.ts
/** Conversation: home and threads (narrow, presence line). Squad: Squad's own wide screens (presence line). Cockpit: a legacy screen kept until Task 5. */
export type Surface = 'conversation' | 'squad' | 'cockpit';

const SQUAD = ['/approvals', '/portfolio', '/review-room', '/oversight'];

export function surfaceOf(pathname: string): Surface {
  if (pathname === '/' || pathname === '/clients' || (pathname.startsWith('/clients/') && !pathname.includes('/file'))) return 'conversation';
  if (SQUAD.some((p) => pathname === p || pathname.startsWith(`${p}/`)) || /^\/clients\/[^/]+\/file/.test(pathname)) return 'squad';
  return 'cockpit';
}
