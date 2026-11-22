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

// The client the shots and the checks open: the legacy book's breach, or the innovation book's first client.
const BREACH = process.env.SHOT_CLIENT ?? 'corvane-analytics';

/**
 * The screens to capture and check. `path` may be a function of the page (to look up an id through
 * the API); `prepare` drives the page into the state worth looking at. `signedOut` skips sign-in.
 */
export const PAGES = [
  { name: 'sign-in', path: '/sign-in', signedOut: true },
  { name: 'home', path: '/' },
  { name: 'thread', path: `/clients/${BREACH}` },
  { name: 'client-file', path: `/clients/${BREACH}/file` },
  { name: 'spreads', path: `/clients/${BREACH}/file/spreads` },
  { name: 'covenants', path: `/clients/${BREACH}/file/covenants` },
  { name: 'documents', path: `/clients/${BREACH}/file/documents` },
  { name: 'funding', path: `/clients/${BREACH}/file/funding` },
  { name: 'history', path: `/clients/${BREACH}/file/history` },
  { name: 'portfolio', path: '/portfolio' },
  { name: 'oversight', path: '/oversight' },
];

export async function signIn(page, email = ANALYST) {
  await page.goto(`${BASE}/sign-in`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(`${BASE}/`);
  await page.locator('.sq-main').waitFor();
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
