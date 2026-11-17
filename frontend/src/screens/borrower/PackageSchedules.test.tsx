import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { PackageSchedules, runSentences, type PackageSchedule } from './PackageSchedules';

const schedule = (over: Partial<PackageSchedule> = {}): PackageSchedule => ({
  id: 'ps-1',
  title: 'Quarterly review package',
  scope: 'borrower',
  borrower_id: 'b-1',
  cadence: 'quarterly',
  days_after_period_end: 45,
  formats: ['docx', 'xlsx'],
  active: true,
  next_run: '2026-11-14',
  ...over,
});

const manager: ApiUser = { id: 'u-1', email: 'pm@bankofstoic.example', name: 'Dana Whitfield', title: 'Portfolio Manager', role: 'portfolio_manager', permissions: ['view', 'release_package'] };
const analyst: ApiUser = { ...manager, id: 'u-2', name: 'Priya Raman', role: 'analyst', permissions: ['view'] };

function mockApi(rows: PackageSchedule[], posts: Record<string, { status?: number; body: unknown }> = {}) {
  const sent: Array<{ url: string; body: unknown }> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        sent.push({ url, body: JSON.parse(String(init.body)) });
        const hit = posts[url];
        const status = hit?.status ?? (hit ? 200 : 404);
        return { ok: status < 300, status, text: async () => JSON.stringify(hit?.body ?? { detail: 'Not found' }) } as Response;
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(rows) } as Response;
    }),
  );
  return sent;
}

function show(user: ApiUser) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = { user, status: 'signed-in' as const, can: (permission: string) => user.permissions.includes(permission), signIn: async () => user, signOut: async () => {}, retry: () => {} };
  return render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <PackageSchedules borrowerId="b-1" borrowerName="Larkspur Environmental Services, Inc." />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('what a run of the due schedules did, in words', () => {
  const titles = { 'ps-1': 'Quarterly review package', 'ps-2': 'Portfolio pack' };

  it('says so when nothing was due', () => {
    expect(runSentences({ today: '2026-11-17', runs: [] }, titles)).toEqual([{ tone: 'neutral', text: 'No schedule was due on 17 Nov 2026. Nothing was generated.' }]);
  });

  it('says a package was prepared, never that it was released, and quotes the server when one could not be assembled', () => {
    const lines = runSentences(
      {
        today: '2026-11-17',
        runs: [
          { schedule_id: 'ps-1', period_end: '2026-09-30', package_id: 'p-1', error: null, next_run: '2027-02-14' },
          { schedule_id: 'ps-2', period_end: '2026-09-30', package_id: null, error: 'no cycle exists for the period', next_run: '2026-11-14' },
          { schedule_id: 'ps-9', period_end: '2026-10-31', package_id: 'p-2', error: null, next_run: null },
        ],
      },
      titles,
    );
    expect(lines).toEqual([
      { tone: 'neutral', text: 'Quarterly review package, Q3 2026: a package was prepared, not released. Next run 14 Feb 2027.' },
      { tone: 'attention', text: 'Portfolio pack, Q3 2026: not generated. The server said: “no cycle exists for the period” The schedule stays due and will be tried again.' },
      { tone: 'neutral', text: 'A schedule, 31 Oct 2026: a package was prepared, not released.' },
    ]);
  });
});

describe('package schedules on the packages tab', () => {
  it('lists the schedules that cover the borrower and counts the rest', async () => {
    mockApi([schedule(), schedule({ id: 'ps-2', title: 'Portfolio pack', scope: 'portfolio', borrower_id: null, cadence: 'monthly', days_after_period_end: 1, formats: ['pptx'], next_run: null }), schedule({ id: 'ps-3', borrower_id: 'b-2' })]);
    show(manager);
    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows.map((row) => within(row).getAllByRole('cell').map((cell) => cell.textContent).join(' | '))).toEqual([
      'This borrower | Quarterly | 45 days after period end | Word, Excel | 14 Nov 2026',
      'The whole portfolio | Monthly | 1 day after period end | PowerPoint | Not set',
    ]);
    expect(screen.getByText(/more schedule is for other borrowers/)).toBeInTheDocument();
  });

  it('offers creating and running only to a role that may release packages', async () => {
    mockApi([schedule()]);
    show(analyst);
    await screen.findByRole('table');
    expect(screen.queryByRole('button', { name: 'Run schedules that are due' })).toBeNull();
    expect(screen.queryByRole('form', { name: 'New package schedule' })).toBeNull();
    expect(screen.getByText('Creating and running schedules needs a portfolio manager or a credit officer. Your role, Credit analyst, can read them.')).toBeInTheDocument();
  });

  it('checks the form, sends exactly the fields the route takes, and shows a refusal in the server’s words', async () => {
    const sent = mockApi([], { '/api/v1/package-schedules': { status: 422, body: { detail: 'a borrower schedule needs a borrower that exists' } } });
    show(manager);
    const form = await screen.findByRole('form', { name: 'New package schedule' });
    await userEvent.clear(within(form).getByLabelText('Days after period end'));
    await userEvent.type(within(form).getByLabelText('Days after period end'), '-5');
    await userEvent.click(within(form).getByRole('button', { name: 'Create the schedule' }));
    expect(within(form).getByLabelText('Title')).toHaveAccessibleDescription('Give the schedule a title.');
    expect(within(form).getByLabelText('Days after period end')).toHaveAccessibleDescription('Enter a whole number of days, zero or more.');
    expect(sent).toEqual([]);

    await userEvent.type(within(form).getByLabelText('Title'), 'Quarterly review package');
    await userEvent.clear(within(form).getByLabelText('Days after period end'));
    await userEvent.type(within(form).getByLabelText('Days after period end'), '45');
    await userEvent.click(within(form).getByRole('checkbox', { name: 'PowerPoint' }));
    await userEvent.click(within(form).getByRole('button', { name: 'Create the schedule' }));
    await waitFor(() =>
      expect(sent).toEqual([
        { url: '/api/v1/package-schedules', body: { title: 'Quarterly review package', scope: 'borrower', borrower_id: 'b-1', cadence: 'quarterly', days_after_period_end: 45, formats: ['docx', 'xlsx'], next_run: null } },
      ]),
    );
    expect(await within(form).findByRole('alert')).toHaveTextContent('Not created: the server refused this. The server said: “a borrower schedule needs a borrower that exists”');
  });

  it('runs what is due and reports it in an announced region', async () => {
    mockApi([schedule()], { '/api/v1/package-schedules/run': { body: { today: '2026-11-17', runs: [{ schedule_id: 'ps-1', period_end: '2026-09-30', package_id: 'p-1', error: null, next_run: '2027-02-14' }] } } });
    show(manager);
    await screen.findByRole('table');
    await userEvent.click(screen.getByRole('button', { name: 'Run schedules that are due' }));
    const line = await screen.findByText('Quarterly review package, Q3 2026: a package was prepared, not released. Next run 14 Feb 2027.');
    expect(line.closest('[aria-live="polite"]')).not.toBeNull();
  });
});
