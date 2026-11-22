import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { Documents } from '../clientfile/views';

vi.mock('@/api/hooks', () => ({ useDocuments: () => ({ data: [], isPending: false, error: null }) }));
vi.mock('../api/hooks', () => ({ useDocumentTypeWords: () => ({ data: undefined }), useSignalWordsTable: () => ({ data: undefined }) }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: () => {}, close: () => {}, current: null }) }));
vi.mock('@/squad/clientfile/UploadDocument', () => ({ UploadDocument: () => null }));
vi.mock('@/squad/clientfile/RunStage', () => ({ RunStage: () => null }));
vi.mock('@/squad/clientfile/review/Commentary', () => ({ Commentary: () => null }));

function mount(permissions: string[]) {
  const user: ApiUser = { id: 'u', email: 'e', name: 'N', title: '', role: 'credit_review', permissions };
  const root = createRootRoute({ component: () => <Documents borrower={{ id: 'b1', code: 'QFL' } as never} /> });
  const router = createRouter({ routeTree: root.addChildren([createRoute({ getParentRoute: () => root, path: '/', component: () => null })]), history: createMemoryHistory({ initialEntries: ['/'] }) });
  return render(
    <AuthContext.Provider value={{ user, status: 'signed-in', can: (p: string) => permissions.includes(p), signIn: async () => user, signOut: async () => {}, retry: () => {} }}>
      <RouterProvider router={router as never} />
    </AuthContext.Provider>,
  );
}

describe('File a document', () => {
  it('is offered only to a role the server lets file documents', async () => {
    const { unmount } = mount(['view', 'upload_document']);
    expect(await screen.findByRole('button', { name: 'File a document' })).toBeInTheDocument();
    unmount();
    mount(['view']);
    await screen.findByText('No document is on file for this client.');
    expect(screen.queryByRole('button', { name: 'File a document' })).not.toBeInTheDocument();
  });
});
