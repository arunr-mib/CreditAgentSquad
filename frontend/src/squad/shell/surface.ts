// frontend/src/squad/shell/surface.ts
/** Conversation: home and threads (a narrow column). Squad: every other screen (wider). Both carry the presence line. */
export type Surface = 'conversation' | 'squad';

export function surfaceOf(pathname: string): Surface {
  return pathname === '/' || pathname === '/clients' || (pathname.startsWith('/clients/') && !/^\/clients\/[^/]+\/file/.test(pathname))
    ? 'conversation'
    : 'squad';
}
