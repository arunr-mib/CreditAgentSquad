import { createContext, useContext } from 'react';
import type { ApiUser } from '@/api/schema';

export interface AuthValue {
  user: ApiUser | null;
  status: 'loading' | 'signed-in' | 'signed-out' | 'unreachable';
  can: (permission: string) => boolean;
  signIn: (email: string, password: string) => Promise<ApiUser>;
  signOut: () => Promise<void>;
  retry: () => void;
}

export const AuthContext = createContext<AuthValue>({
  user: null,
  status: 'loading',
  can: () => false,
  signIn: async () => {
    throw new Error('No auth provider');
  },
  signOut: async () => {},
  retry: () => {},
});

export function useAuth(): AuthValue {
  return useContext(AuthContext);
}
