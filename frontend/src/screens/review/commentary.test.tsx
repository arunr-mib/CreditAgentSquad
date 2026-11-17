import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser, ReviewSheetDetail } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { Commentary } from './Commentary';
import { insertReference, sheetFigures } from './CommentaryEditor';

const LEVERAGE = '11111111-1111-4111-8111-111111111111';
const MARGIN = '22222222-2222-4222-8222-222222222222';

const sheet = (over: Partial<ReviewSheetDetail> = {}): ReviewSheetDetail => ({
  id: 's-1',
  borrower_id: 'b-1',
  borrower_name: 'Larkspur Environmental Services, Inc.',
  cycle_id: 'c-1',
  meeting_id: null,
  status: 'draft',
  period_end: '2026-09-30',
  approved_by: null,
  approved_at: null,
  approved_by_name: null,
  content: { fact_labels: { [LEVERAGE]: 'Total debt to EBITDA, Sep 30, 2026', [MARGIN]: 'EBITDA margin, Sep 30, 2026' } },
  changes_since_last: [],
  facts: {
    [LEVERAGE]: { value: '1.48', unit: 'ratio', kind: 'calculated', status: 'verified', key: 'metric.leverage', period_end: '2026-09-30' },
    [MARGIN]: { value: '0.097', unit: 'pct', kind: 'calculated', status: 'verified', key: 'metric.ebitda_margin', period_end: '2026-09-30' },
  },
  commentary: [
    { id: 'k-1', section: 'summary', version: 1, body: 'Stand-in draft for the reviewer to replace.', rendered: '', fact_ids: [], author_type: 'agent', author_name: 'Review Agent', written_by_agent: true, status: 'draft', agent_run_id: 'r-1', created_at: '2026-11-17T08:00:00' },
  ],
  ...over,
});

const FACTS = {
  [LEVERAGE]: { id: LEVERAGE, key: 'metric.leverage', label: 'Total debt to EBITDA', value: '1.48', unit: 'ratio', kind: 'calculated', status: 'verified', period_end: '2026-09-30', months: 0, borrower_id: 'b-1', document_id: null, page: null, calc_run_id: 'c-9' },
};

function mockApi(write: { status?: number; body: unknown }) {
  const posts: Array<{ url: string; body: unknown }> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        posts.push({ url, body: JSON.parse(String(init.body)) });
        const status = write.status ?? 200;
        return { ok: status < 300, status, text: async () => JSON.stringify(write.body) } as Response;
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(url.startsWith('/api/v1/ui/facts') ? FACTS : {}) } as Response;
    }),
  );
  return posts;
}

const analyst: ApiUser = { id: 'u-1', email: 'analyst@bankofstoic.example', name: 'Priya Raman', title: 'Credit analyst', role: 'analyst', permissions: ['view', 'edit_commentary'] };
const reviewer: ApiUser = { ...analyst, id: 'u-2', role: 'credit_review', permissions: ['view'] };

function show(data: ReviewSheetDetail, user: ApiUser = analyst) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = { user, status: 'signed-in' as const, can: (permission: string) => user.permissions.includes(permission), signIn: async () => user, signOut: async () => {}, retry: () => {} };
  return render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <Commentary sheet={data} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('a fact reference in commentary', () => {
  it('goes where the caret is, replaces a selection, and leaves the caret after it', () => {
    expect(insertReference('Leverage was  at period end.', 13, 13, 'f-1')).toEqual({ text: 'Leverage was {{fact:f-1}} at period end.', caret: 25 });
    expect(insertReference('Leverage was 1.48x.', 13, 18, 'f-1')).toEqual({ text: 'Leverage was {{fact:f-1}}.', caret: 25 });
    expect(insertReference('', 0, 0, 'f-1')).toEqual({ text: '{{fact:f-1}}', caret: 12 });
    // A caret beyond the text (the text shrank) falls back to the end.
    expect(insertReference('Short', 40, 60, 'f-1').text).toBe('Short{{fact:f-1}}');
  });

  it('is offered for every fact on the sheet, named as the sheet names it and shown as the workspace shows it', () => {
    expect(sheetFigures(sheet())).toEqual([
      { id: MARGIN, label: 'EBITDA margin, Sep 30, 2026', text: '9.7%', kind: 'calculated' },
      { id: LEVERAGE, label: 'Total debt to EBITDA, Sep 30, 2026', text: '1.48x', kind: 'calculated' },
    ]);
  });
});

describe('editing commentary in the review room', () => {
  it('offers no editing to a role that cannot write commentary, or on a released sheet', () => {
    mockApi({ body: {} });
    const { unmount } = show(sheet(), reviewer);
    expect(screen.queryByRole('button', { name: /Edit|Write this section/ })).toBeNull();
    expect(screen.getByText(/Writing commentary needs a credit analyst or a portfolio manager\. Your role, Credit review, can read it\./)).toBeInTheDocument();
    unmount();
    show(sheet({ status: 'released' }));
    expect(screen.queryByRole('button', { name: /Edit|Write this section/ })).toBeNull();
    expect(screen.getByText('This review sheet is released: its commentary can no longer be edited.')).toBeInTheDocument();
  });

  it('inserts a picked figure as a reference at the caret, saves, and shows the server’s warnings', async () => {
    const saved = sheet({ commentary: [{ ...sheet().commentary[0]!, id: 'k-2', version: 2, written_by_agent: false, author_type: 'user', author_name: 'Priya Raman', body: `Leverage was {{fact:${LEVERAGE}}}, against 2.5 times allowed.` }] });
    const posts = mockApi({ body: { ...saved, warnings: ['2.5: a figure was typed, not referenced, and matches no fact or cited quote'] } });
    const view = show(sheet());
    await userEvent.click(screen.getByRole('button', { name: 'Edit summary' }));
    const editor = screen.getByRole('form', { name: 'Edit summary' });
    const area = within(editor).getByRole('textbox');
    expect(area).toHaveValue('Stand-in draft for the reviewer to replace.');
    await userEvent.clear(area);
    await userEvent.type(area, 'Leverage was , against 2.5 times allowed.');
    (area as HTMLTextAreaElement).setSelectionRange(13, 13);

    await userEvent.click(within(editor).getByRole('button', { name: 'Insert a figure' }));
    const find = await screen.findByRole('combobox', { name: 'Find a figure on this sheet' });
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual(['EBITDA margin, Sep 30, 20269.7%', 'Total debt to EBITDA, Sep 30, 20261.48x']);
    await userEvent.type(find, 'debt');
    expect(screen.getAllByRole('option')).toHaveLength(1);
    await userEvent.keyboard('{Enter}');
    expect(area).toHaveValue(`Leverage was {{fact:${LEVERAGE}}}, against 2.5 times allowed.`);
    // The preview shows the stored figure, not the reference.
    expect(await within(editor).findByRole('button', { name: /^1\.48x, Total debt to EBITDA/ })).toBeInTheDocument();

    await userEvent.click(within(editor).getByRole('button', { name: 'Save as a draft' }));
    await waitFor(() => expect(posts).toEqual([{ url: '/api/v1/review-sheets/s-1/commentary', body: { section: 'summary', body: `Leverage was {{fact:${LEVERAGE}}}, against 2.5 times allowed.` } }]));
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <AuthContext.Provider value={{ user: analyst, status: 'signed-in', can: (permission) => analyst.permissions.includes(permission), signIn: async () => analyst, signOut: async () => {}, retry: () => {} }}>
          <Commentary sheet={saved} />
        </AuthContext.Provider>
      </QueryClientProvider>,
    );
    const notice = await screen.findByRole('alert');
    expect(notice).toHaveTextContent('Summary saved as a draft, with 1 warning from the server');
    expect(notice).toHaveTextContent('2.5: a figure was typed, not referenced, and matches no fact or cited quote');
    expect(screen.queryByRole('form', { name: 'Edit summary' })).toBeNull();
  });

  it('shows a refusal beside the editor in the server’s words and keeps the text', async () => {
    mockApi({ status: 422, body: { detail: 'reference to a fact that is not in scope: 00000000' } });
    show(sheet());
    await userEvent.click(screen.getByRole('button', { name: 'Edit summary' }));
    const editor = screen.getByRole('form', { name: 'Edit summary' });
    const area = within(editor).getByRole('textbox');
    await userEvent.clear(area);
    await userEvent.click(within(editor).getByRole('button', { name: 'Save as a draft' }));
    expect(area).toHaveAccessibleDescription('Write the section before saving it.');
    await userEvent.type(area, 'Margin fell.');
    await userEvent.click(within(editor).getByRole('button', { name: 'Save as a draft' }));
    expect(await within(editor).findByRole('alert')).toHaveTextContent('Not recorded: the server refused this. The server said: “reference to a fact that is not in scope: 00000000”');
    expect(area).toHaveValue('Margin fell.');
  });

  it('lets a person write a section that does not exist yet', async () => {
    const posts = mockApi({ body: { ...sheet(), warnings: [] } });
    show(sheet());
    await userEvent.click(screen.getByRole('button', { name: 'Write this section' }));
    const editor = screen.getByRole('form', { name: 'Edit performance' });
    expect(within(editor).getByText('Not yet written; saved as version 1, written by you')).toBeInTheDocument();
    await userEvent.type(within(editor).getByRole('textbox'), 'Revenue grew on new contracts.');
    await userEvent.click(within(editor).getByRole('button', { name: 'Save as a draft' }));
    await waitFor(() => expect(posts[0]?.body).toEqual({ section: 'performance', body: 'Revenue grew on new contracts.' }));
  });
});
