// Builds the app when needed and serves dist/ with `vite preview`. Shared by screenshots.mjs and a11y.mjs.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const PORT = Number(process.env.PREVIEW_PORT ?? 4173);
export const BASE = `http://127.0.0.1:${PORT}`;

export const PAGES = [
  { name: 'command-centre', path: '/showcase/command-centre' },
  { name: 'covenant-workspace', path: '/showcase/covenants' },
  { name: 'spread-grid', path: '/showcase/spread' },
  { name: 'design', path: '/design' },
];

async function reachable() {
  try {
    const response = await fetch(BASE, { signal: AbortSignal.timeout(1000) });
    return response.ok;
  } catch {
    return false;
  }
}

/** Returns a function that stops the server (a no-op when one was already running). */
export async function serve({ rebuild = !process.argv.includes('--no-build') } = {}) {
  if (await reachable()) return () => {};
  if (rebuild || !existsSync(resolve(root, 'dist/index.html'))) {
    const build = spawnSync('pnpm', ['build'], { cwd: root, stdio: 'inherit' });
    if (build.status !== 0) throw new Error('Build failed');
  }
  const server = spawn('pnpm', ['exec', 'vite', 'preview', '--port', String(PORT), '--strictPort', '--host', '127.0.0.1'], {
    cwd: root,
    stdio: 'ignore',
    detached: true,
  });
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (await reachable()) {
      return () => {
        try {
          process.kill(-server.pid);
        } catch {
          /* already stopped */
        }
      };
    }
    await new Promise((done) => setTimeout(done, 250));
  }
  process.kill(-server.pid);
  throw new Error(`Preview server did not start on ${BASE}`);
}
