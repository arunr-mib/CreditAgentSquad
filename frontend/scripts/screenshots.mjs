// Captures the three showcase screens and the /design page at 1440 x 900, device scale factor 2.
// Usage: node scripts/screenshots.mjs [--no-build] [--full]
//   --full also writes full-page captures as <name>-full.png.
// Uses the globally installed Playwright; nothing is downloaded.
import { mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { BASE, PAGES, root, serve } from './serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const outDir = resolve(root, 'screenshots');
mkdirSync(outDir, { recursive: true });

const stop = await serve();
const browser = await chromium.launch();
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' });
  const page = await context.newPage();
  for (const target of PAGES) {
    await page.goto(`${BASE}${target.path}`, { waitUntil: 'networkidle' });
    await page.waitForSelector('[data-ready]');
    await page.evaluate(() => document.fonts.ready);
    const file = resolve(outDir, `${target.name}.png`);
    await page.screenshot({ path: file });
    console.log(`wrote ${file}`);
    if (process.argv.includes('--full')) {
      // Grow the viewport to the document so sticky elements settle where they sit when scrolled into view.
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
      await page.setViewportSize({ width: 1440, height });
      const full = resolve(outDir, `${target.name}-full.png`);
      await page.screenshot({ path: full });
      console.log(`wrote ${full}`);
      await page.setViewportSize({ width: 1440, height: 900 });
    }
  }
} finally {
  await browser.close();
  stop();
}
