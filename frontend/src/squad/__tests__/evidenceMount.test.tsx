import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useSource } from '@/source/context';
import { SourceProvider } from '@/source/SourceDrawer';

window.scrollTo = () => {};

function Opener() {
  const source = useSource();
  return (
    <button type="button" onClick={() => source.open({ type: 'fact', id: 'f1' })}>
      open
    </button>
  );
}

function renderIn(squad: boolean) {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404, text: async () => '{"detail":"Not found"}' }) as Response));
  const tree = (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <SourceProvider>
        {squad ? (
          <div className="sq-root">
            <Opener />
          </div>
        ) : (
          <Opener />
        )}
      </SourceProvider>
    </QueryClientProvider>
  );
  render(tree);
}

afterEach(() => vi.unstubAllGlobals());

describe('where the evidence drawer mounts', () => {
  it('inside the Squad root, so it reads the look', async () => {
    renderIn(true);
    await userEvent.click(screen.getByRole('button', { name: 'open' }));
    const drawer = await screen.findByRole('dialog');
    expect(drawer.closest('.sq-root')).not.toBeNull();
  });

  it('on the page body in the legacy cockpit, unchanged', async () => {
    renderIn(false);
    await userEvent.click(screen.getByRole('button', { name: 'open' }));
    const drawer = await screen.findByRole('dialog');
    expect(drawer.parentElement).toBe(document.body);
  });
});
