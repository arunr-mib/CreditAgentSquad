// Builds the app when needed and serves dist/ with `vite preview` (which proxies /api to the API on
// port 8000, as the dev server does). Shared by screenshots.mjs and a11y.mjs.
// Both scripts need the seeded stack running: see docs/HANDOFF.md, "Running it".
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const PORT = Number(process.env.PREVIEW_PORT ?? 4173);
export const BASE = `http://127.0.0.1:${PORT}`;
export const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
export const ANALYST = 'priya.raman@bankofstoic.example';

const BREACH = 'kestrel-bay-packaging';

/** Opens the source drawer on a figure and waits for the page to be drawn with its highlight. */
async function openSource(page, row, pick) {
  const line = page.locator('main table tbody tr').filter({ hasText: row }).first();
  await pick(line).click();
  await page.locator('[data-source-drawer]').waitFor();
}

async function waitForPage(page, scope = '[data-source-drawer]') {
  await page.locator(`${scope} [data-pdf-page="ready"]`).first().waitFor({ timeout: 30000 });
  await page.locator(`${scope} [data-mark][data-active]`).first().waitFor();
}

/**
 * The screens to capture and check. `path` may be a function of the page (to look up an id through
 * the API); `prepare` drives the page into the state worth looking at. `signedOut` skips sign-in.
 */
export const PAGES = [
  { name: 'sign-in', path: '/sign-in', signedOut: true },
  { name: 'command-centre', path: '/command-centre' },
  { name: 'portfolio', path: '/portfolio' },
  { name: 'borrower-summary', path: `/borrowers/${BREACH}` },
  { name: 'loans', path: '/borrowers/vantry-freight/loans' },
  { name: 'documents', path: `/borrowers/${BREACH}/documents` },
  {
    name: 'document-viewer',
    path: async (page) => {
      const id = await page.evaluate(async (code) => {
        const borrowers = await (await fetch('/api/v1/borrowers')).json();
        const borrower = borrowers.find((row) => row.code === code);
        const documents = await (await fetch(`/api/v1/borrowers/${borrower.id}/documents`)).json();
        return documents.find((doc) => doc.doc_type === 'interim_statements').id;
      }, BREACH);
      return `/borrowers/${BREACH}/documents/${id}?page=3`;
    },
    prepare: async (page) => {
      await page.locator('main [data-pdf-page="ready"]').waitFor({ timeout: 30000 });
      await page.locator('main [data-mark]').first().waitFor();
    },
  },
  { name: 'spreads', path: `/borrowers/${BREACH}/spreads` },
  {
    name: 'spread-source',
    path: `/borrowers/${BREACH}/spreads`,
    prepare: async (page) => {
      await openSource(page, 'Net revenue', (line) => line.getByRole('button').last());
      await waitForPage(page);
    },
  },
  { name: 'covenants', path: `/borrowers/${BREACH}/covenants` },
  {
    name: 'covenant-source',
    path: `/borrowers/${BREACH}/covenants`,
    prepare: async (page) => {
      await openSource(page, 'Total Leverage Ratio', (line) => line.getByRole('button', { name: /Calculated by code/ }).first());
      await page.locator('[data-source-drawer]').getByText('Total debt ÷ EBITDA').waitFor();
    },
  },
  { name: 'borrowing-base', path: '/borrowers/briarstone-beverage/borrowing-base' },
  { name: 'signals', path: '/borrowers/thornbury-metal/signals' },
  { name: 'timeline', path: `/borrowers/${BREACH}/timeline` },
  { name: 'calendar', path: '/calendar' },
  { name: 'review-room', path: '/review-room' },
  {
    // The panel is opened but nothing is asked: a question starts an agent run, and a live model is billable.
    name: 'copilot',
    path: `/borrowers/${BREACH}/covenants`,
    prepare: async (page) => {
      await page.getByRole('button', { name: 'Copilot' }).click();
      await page.locator('[data-copilot]').waitFor();
    },
  },
  { name: 'agent-activity', path: '/agent-activity' },
  { name: 'governance', path: '/governance' },
  { name: 'design', path: '/design' },
];

export async function signIn(page, email = ANALYST) {
  await page.goto(`${BASE}/sign-in`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL('**/command-centre**');
  await page.waitForSelector('[data-ready]');
}

/** Goes to a target and waits until it is worth looking at. */
export async function open(page, target) {
  const path = typeof target.path === 'function' ? await target.path(page) : target.path;
  await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-ready]', { timeout: 30000 });
  if (target.prepare) await target.prepare(page);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState('networkidle');
  return path;
}

async function waitForServer(timeoutMs = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(BASE);
      if (response.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((done) => setTimeout(done, 200));
  }
  throw new Error(`Preview server did not start on ${BASE}`);
}

async function requireApi() {
  try {
    const response = await fetch(`${BASE}/api/v1/health`);
    if (response.ok) return;
  } catch {
    // fall through
  }
  throw new Error('The API is not reachable through the preview server. Start it on port 8000 with the seeded book (see docs/HANDOFF.md).');
}

/** Returns a function that stops the server. */
export async function serve() {
  if (!process.argv.includes('--no-build') || !existsSync(resolve(root, 'dist/index.html'))) {
    const build = spawnSync('pnpm', ['build'], { cwd: root, stdio: 'inherit' });
    if (build.status !== 0) throw new Error('Build failed');
  }
  const server = spawn('pnpm', ['exec', 'vite', 'preview', '--port', String(PORT), '--strictPort', '--host', '127.0.0.1'], { cwd: root, stdio: 'ignore' });
  const stop = () => server.kill('SIGTERM');
  try {
    await waitForServer();
    await requireApi();
  } catch (error) {
    stop();
    throw error;
  }
  return stop;
}
