// Accessibility check: axe-core on the four pages, plus a keyboard pass that tabs through every
// focusable control and fails if one takes focus without a visible focus ring.
// Usage: node scripts/a11y.mjs [--no-build]
// Uses the globally installed Playwright and the axe-core dev dependency; nothing is downloaded.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { BASE, PAGES, serve } from './serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

const stop = await serve();
const browser = await chromium.launch();
let failed = false;

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();

  for (const target of PAGES) {
    await page.goto(`${BASE}${target.path}`, { waitUntil: 'networkidle' });
    await page.waitForSelector('[data-ready]');
    await page.evaluate(() => document.fonts.ready);

    // 1. axe-core, WCAG 2.1 A and AA plus best practices.
    await page.evaluate(axeSource);
    const result = await page.evaluate(() =>
      window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] } }),
    );
    const counts = { critical: 0, serious: 0, moderate: 0, minor: 0 };
    for (const violation of result.violations) counts[violation.impact] += violation.nodes.length;
    console.log(
      `${target.path}: axe ${result.passes.length} rules passed; violations critical ${counts.critical}, serious ${counts.serious}, moderate ${counts.moderate}, minor ${counts.minor}`,
    );
    for (const violation of result.violations) {
      console.log(`  [${violation.impact}] ${violation.id}: ${violation.help} (${violation.nodes.length})`);
      for (const node of violation.nodes.slice(0, 3)) console.log(`      ${node.target.join(' ')}`);
    }
    if (counts.critical + counts.serious > 0) failed = true;

    // 2. Keyboard pass: every tab stop must show a focus ring.
    const expected = await page.evaluate(
      () =>
        [...document.querySelectorAll('a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])')].filter((element) => {
          const box = element.getBoundingClientRect();
          return box.width > 0 && box.height > 0 && getComputedStyle(element).visibility !== 'hidden';
        }).length,
    );
    await page.evaluate(() => {
      window.scrollTo(0, 0);
      document.activeElement?.blur?.();
    });
    const seen = new Set();
    const missingRing = [];
    for (let step = 0; step < expected + 20; step += 1) {
      await page.keyboard.press('Tab');
      const info = await page.evaluate(() => {
        const element = document.activeElement;
        if (!element || element === document.body) return null;
        element.dataset.a11ySeen ??= String(Math.random());
        const style = getComputedStyle(element);
        const ring = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) >= 2;
        const within = element.closest('.focus-within\\:outline-2');
        const withinRing = within ? getComputedStyle(within).outlineStyle !== 'none' && parseFloat(getComputedStyle(within).outlineWidth) >= 2 : false;
        return {
          key: element.dataset.a11ySeen,
          ring: ring || withinRing,
          label: `${element.tagName.toLowerCase()} "${(element.getAttribute('aria-label') ?? element.textContent ?? '').trim().slice(0, 50)}"`,
        };
      });
      if (!info) continue;
      if (seen.has(info.key)) break;
      seen.add(info.key);
      if (!info.ring) missingRing.push(info.label);
    }
    console.log(`${target.path}: keyboard reached ${seen.size} of ${expected} tab stops; ${missingRing.length} without a visible focus ring`);
    for (const label of missingRing) console.log(`      no ring: ${label}`);
    // Roving-focus groups (table rows, segmented controls, tabs) expose one tab stop each, so reached can be below the total.
    if (missingRing.length > 0) failed = true;
  }
} finally {
  await browser.close();
  stop();
}

console.log(
  failed
    ? 'FAILED: serious or critical violations, or controls without a focus ring'
    : 'PASSED: no serious or critical violations; every tab stop shows a focus ring',
);
process.exit(failed ? 1 : 0);
