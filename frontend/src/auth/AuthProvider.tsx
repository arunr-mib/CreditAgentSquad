import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, type ReactNode } from 'react';
import { ApiError, onUnauthorized, request } from '@/api/client';
import type { ApiUser } from '@/api/schema';
import { AuthContext, type AuthValue } from './context';

const ME = ['me'] as const;

/**
 * Who is signed in. The session is a cookie the server sets; the workspace only asks "who am I".
 * Any 401 from any request ends the session here, and the router sends the person to sign in.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const me = useQuery({
    queryKey: ME,
    queryFn: async (): Promise<ApiUser | null> => {
      try {
        return await request<ApiUser>('/auth/me', { quiet401: true });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: Infinity,
    retry: false,
  });

  useEffect(() => onUnauthorized(() => client.setQueryData(ME, null)), [client]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const user = await request<ApiUser>('/auth/login', { method: 'POST', body: { email, password }, quiet401: true });
      // Nothing read by the previous person may be shown to the next one.
      client.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' });
      client.setQueryData(ME, user);
      return user;
    },
    [client],
  );

  const signOut = useCallback(async () => {
    try {
      await request<void>('/auth/logout', { method: 'POST', body: {}, quiet401: true });
    } finally {
      client.setQueryData(ME, null);
      client.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' });
    }
  }, [client]);

  const value = useMemo<AuthValue>(() => {
    const user = me.data ?? null;
    return {
      user,
      status: me.isPending ? 'loading' : me.isError ? 'unreachable' : user ? 'signed-in' : 'signed-out',
      can: (permission) => Boolean(user?.permissions.includes(permission)),
      signIn,
      signOut,
      retry: () => void me.refetch(),
    };
  }, [me, signIn, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
