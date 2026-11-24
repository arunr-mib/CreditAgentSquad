import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ApiError } from '@/api/client';
import { WordsGate } from '@/api/words';
import { AuthProvider } from '@/auth/AuthProvider';
import { ToastProvider, TooltipProvider } from '@/design';
import { router } from './router';
import './styles.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // A refusal (401, 403, 404, 422) will not change on a second try; a dropped connection might.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 1,
    },
  },
});

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <WordsGate>
        <AuthProvider>
          <TooltipProvider delayDuration={300}>
            <ToastProvider>
              <RouterProvider router={router} />
            </ToastProvider>
          </TooltipProvider>
        </AuthProvider>
      </WordsGate>
    </QueryClientProvider>
  </StrictMode>,
);
