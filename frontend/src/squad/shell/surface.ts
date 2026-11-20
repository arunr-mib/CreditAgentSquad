// frontend/src/squad/shell/surface.ts
/** Squad's own routes (home, a client's thread) are a narrow conversation with the presence line; every other route is a cockpit screen kept from the legacy workspace. */
export type Surface = 'conversation' | 'cockpit';

export function surfaceOf(pathname: string): Surface {
  return pathname === '/' || pathname === '/clients' || pathname.startsWith('/clients/') ? 'conversation' : 'cockpit';
}
