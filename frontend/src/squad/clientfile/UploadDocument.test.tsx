import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { UploadDocument } from './UploadDocument';

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <UploadDocument borrowerId="b-1" code="larkspur-environmental" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('filing a document', () => {
  it('sends nothing without a file, and ties the reason to the field', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    show();
    await userEvent.click(screen.getByRole('button', { name: 'File the document' }));
    const field = screen.getByLabelText('Document file');
    expect(field).toBeInvalid();
    expect(field).toHaveAccessibleDescription('Choose a document file first.');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('sends the file and the title as a multipart form, and shows the server’s refusal in its own words', async () => {
    const sent: Array<{ url: string; init: RequestInit }> = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init: RequestInit) => {
        sent.push({ url, init });
        return { ok: false, status: 422, text: async () => JSON.stringify({ detail: 'Only PDF files are accepted.' }) } as Response;
      }),
    );
    show();
    const file = new File(['not a pdf'], 'meeting-notes.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText('Document file'), file);
    expect(screen.getByText('meeting-notes.pdf is ready to file.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Title (optional)'), '  Meeting notes  ');
    await userEvent.click(screen.getByRole('button', { name: 'File the document' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Not filed: the server refused this. The server said: “Only PDF files are accepted.”');
    expect(sent).toHaveLength(1);
    expect(sent[0]?.url).toBe('/api/v1/borrowers/b-1/documents');
    expect(sent[0]?.init.method).toBe('POST');
    // The browser sets the multipart boundary: no JSON content type is forced on a form.
    expect(sent[0]?.init.headers).toEqual({ Accept: 'application/json' });
    const form = sent[0]?.init.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect((form.get('file') as File).name).toBe('meeting-notes.pdf');
    expect(form.get('title')).toBe('Meeting notes');
    // Only the fields the route takes are sent.
    expect([...form.keys()]).toEqual(['file', 'title']);
  });

  it('offers PDF, Excel and CSV files in the picker', () => {
    show();
    const accept = screen.getByLabelText('Document file').getAttribute('accept') ?? '';
    expect(accept).toContain('.pdf');
    expect(accept).toContain('.xlsx');
    expect(accept).toContain('.csv');
  });
});
