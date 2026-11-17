// End-to-end journeys against the running, seeded stack (API on 8000, workspace on 5173).
// Usage: pnpm e2e            (BASE_URL=http://localhost:5173 by default; HEADED=1 to watch)
// Uses the globally installed Playwright; nothing is downloaded.
//
// The officer journey records a real decision, so each run takes one open covenant breach out of
// the queue. A freshly seeded book has four; reseed the dev database when they are used up.
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const ANALYST = 'priya.raman@bankofstoic.example';
const OFFICER = 'helen.strand@bankofstoic.example';
const BORROWER = 'kestrel-bay-packaging';
const failuresDir = resolve(dirname(fileURLToPath(import.meta.url)), 'failures');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function signIn(page, email) {
  await page.goto(`${BASE}/sign-in`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL('**/command-centre**');
  await page.waitForSelector('[data-ready]');
}

async function signOut(page) {
  await page.getByRole('button', { name: /Account menu/ }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();
  await page.waitForURL('**/sign-in**');
}

/** The drawer shows the rendered page with the cited figure outlined inside the page. */
async function expectHighlightedPage(page, printed) {
  const drawer = page.locator('[data-source-drawer]');
  await drawer.locator('[data-pdf-page="ready"]').first().waitFor({ timeout: 30000 });
  const mark = drawer.locator('[data-mark][data-active]').first();
  await mark.waitFor();
  const [markBox, pageBox] = await Promise.all([mark.boundingBox(), drawer.locator('[data-pdf-page="ready"] canvas').first().boundingBox()]);
  assert(markBox && pageBox, 'the highlight and the page are both drawn');
  assert(markBox.x >= pageBox.x - 4 && markBox.x + markBox.width <= pageBox.x + pageBox.width + 4, 'the highlight sits inside the page, left to right');
  assert(markBox.width > 8 && markBox.height > 4, 'the highlight has a real size');
  const quote = await drawer.locator('blockquote mark').first().textContent();
  assert(quote && quote.includes(printed), `the quoted figure is ${printed}, got ${quote}`);
  // The canvas has ink on it: the PDF really rendered.
  const inked = await drawer.locator('[data-pdf-page="ready"] canvas').first().evaluate((canvas) => {
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let dark = 0;
    for (let i = 0; i < data.length; i += 40) if (data[i] < 120 && data[i + 3] > 0) dark += 1;
    return dark;
  });
  assert(inked > 50, 'the page canvas has text drawn on it');
}

const journeys = [
  {
    name: 'sign in as an analyst; a visitor without a session is sent to sign-in; a wrong password is refused in the server’s words',
    async run(page) {
      await page.goto(`${BASE}/portfolio`);
      await page.waitForURL('**/sign-in**');
      await page.getByLabel('Email').fill(ANALYST);
      await page.getByLabel('Password').fill('not-the-password');
      await page.getByRole('button', { name: 'Sign in', exact: true }).click();
      await page.getByText('Email or password is not correct.').waitFor();
      await page.getByRole('button', { name: /Priya Raman/ }).click();
      await page.getByRole('button', { name: 'Sign in', exact: true }).click();
      // The page asked for before signing in is where the person lands.
      await page.waitForURL('**/portfolio');
      assert((await page.locator('[data-user-name]').textContent()) === 'Priya Raman', 'the shell names the person');
      assert((await page.locator('[data-user-role]').textContent()) === 'Credit analyst', 'the shell shows the role');
      await page.locator('[data-as-of]').filter({ hasText: /\d{1,2} \w{3} \d{4}/ }).waitFor();
    },
  },
  {
    name: 'open the queue and a critical item; the analyst’s attempt to decide a breach is refused plainly',
    async run(page) {
      await signIn(page, ANALYST);
      const rows = page.locator('table tbody tr[data-row]');
      assert((await rows.count()) > 0, 'the queue has items');
      await page.getByRole('radio', { name: /Critical/ }).click();
      const critical = rows.filter({ hasText: 'Kestrel Bay Packaging' }).first();
      if ((await critical.count()) === 0) {
        assert((await rows.count()) > 0, 'there is at least one critical item');
        await rows.first().click();
      } else {
        await critical.click();
      }
      const panel = page.locator('[data-work-item]');
      await panel.waitFor();
      await panel.getByRole('heading', { level: 2 }).waitFor();
      assert((await panel.getByText('Evidence', { exact: true }).count()) === 1, 'the item shows its evidence');
      await panel.getByText('The calculation', { exact: true }).waitFor();
      const before = await rows.count();
      await panel.getByRole('radio').first().check();
      await panel.getByLabel(/Reason/).fill('Journey test: an analyst may not decide the response to a breach.');
      await panel.getByRole('button', { name: 'Record decision' }).click();
      await panel.getByText(/Not recorded: your role cannot decide this item/).waitFor();
      await panel.getByText(/The server said: “your role cannot decide this item/).waitFor();
      assert((await panel.getAttribute('data-item-status')) === 'open', 'the item is still open');
      assert((await rows.count()) === before, 'the item is still in the queue');
    },
  },
  {
    name: 'trace a covenant figure from the covenant table through its calculation to the highlighted source page',
    async run(page) {
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/borrowers/${BORROWER}/covenants`);
      await page.waitForSelector('[data-ready]');
      const row = page.locator('table tbody tr[data-row]').filter({ hasText: 'Total Leverage Ratio' }).first();
      await row.getByRole('button', { name: /Total Leverage Ratio, .*Calculated by code/ }).first().click();
      const drawer = page.locator('[data-source-drawer]');
      await drawer.getByRole('heading', { name: 'Total Leverage Ratio' }).waitFor();
      await drawer.getByText('Total debt ÷ EBITDA').waitFor();
      const calculated = await drawer.locator('[data-source-value]').textContent();
      assert(/^\d+\.\d\dx$/.test(calculated ?? ''), `the drawer shows the ratio, got ${calculated}`);
      // One of the inputs: long-term debt, read from the balance sheet.
      await drawer.getByRole('button', { name: /Long-term debt, net of current portion/ }).first().click();
      await drawer.getByRole('heading', { name: 'Long-term debt, net of current portion' }).waitFor();
      const value = (await drawer.locator('[data-source-value]').textContent()) ?? '';
      const printed = value.replace(/^\$/, '').replace(/,000$/, '');
      await expectHighlightedPage(page, printed);
      await drawer.getByText(/page 2/).first().waitFor();
      // Back returns to the calculation the reader came from.
      await drawer.getByRole('button', { name: 'Back' }).click();
      await drawer.getByRole('heading', { name: 'Total Leverage Ratio' }).waitFor();
      await drawer.getByRole('button', { name: 'Close the source' }).click();
      await drawer.waitFor({ state: 'detached' });
    },
  },
  {
    name: 'open the spread grid, trace a cell to its page, and follow it into the document viewer',
    async run(page) {
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/borrowers/${BORROWER}/spreads`);
      await page.waitForSelector('[data-ready]');
      const row = page.locator('table tbody tr').filter({ hasText: 'Net revenue' }).first();
      const cell = row.getByRole('button').last();
      const label = (await cell.getAttribute('aria-label')) ?? '';
      const printed = label.split(',')[0] + (label.split(',')[1]?.match(/^\d{3}/) ? `,${label.split(',')[1]}` : '');
      assert(/^[\d,]+$/.test(printed), `the cell shows a figure in thousands, got ${label}`);
      await cell.click();
      const drawer = page.locator('[data-source-drawer]');
      await drawer.getByRole('heading', { name: 'Net revenue' }).waitFor();
      await expectHighlightedPage(page, printed);
      await drawer.getByRole('link', { name: /Open in the document viewer/ }).first().click();
      await page.waitForURL(/\/documents\/[0-9a-f-]+\?.*fact=/);
      await page.locator('main [data-pdf-page="ready"]').waitFor({ timeout: 30000 });
      await page.locator('main [data-mark][data-active]').first().waitFor();
      assert((await page.locator('main button[data-figure="is.revenue"]').count()) === 1, 'the viewer lists net revenue among the figures on the page');
    },
  },
  {
    name: 'sign in as a credit officer, record a decision on a breach with a reason, see it leave the queue, and find it in the ledger',
    async run(page) {
      await signIn(page, OFFICER);
      assert((await page.locator('[data-user-role]').textContent()) === 'Credit officer', 'the shell shows the officer’s role');
      const rows = page.locator('table tbody tr[data-row]');
      const before = await rows.count();
      const breaches = rows.filter({ hasText: /is in breach|fails but the certificate reports compliance/ });
      assert((await breaches.count()) > 0, 'an open covenant breach is in the queue (reseed the dev database if earlier runs decided them all)');
      const target = breaches.last();
      const borrower = ((await target.locator('th').first().textContent()) ?? '').trim();
      await target.click();
      const panel = page.locator('[data-work-item]');
      await panel.getByText(/Covenant breach/).first().waitFor();
      const itemId = await panel.getAttribute('data-work-item');
      // A decision that needs a reason is not sent without one.
      await panel.getByRole('radio', { name: /Reserve rights/ }).check();
      await panel.getByRole('button', { name: 'Record decision' }).click();
      await panel.getByText(/This decision needs a reason/).waitFor();
      const reason = `Journey ${new Date().toISOString()}: certificate and calculation disagree; reserve rights pending the borrower's response.`;
      await panel.getByLabel(/Reason/).fill(reason);
      await panel.getByRole('button', { name: 'Record decision' }).click();
      await page.getByText('Recorded: Reserve rights').first().waitFor();
      await page.waitForFunction((expected) => document.querySelectorAll('table tbody tr[data-row]').length === expected, before - 1);
      assert((await page.locator(`[data-work-item="${itemId}"][data-item-status="open"]`).count()) === 0, 'the decided item is no longer shown as open');
      assert((await rows.filter({ hasText: borrower }).filter({ hasText: /is in breach|fails but the certificate reports compliance/ }).count()) === 0, 'the breach left the queue');

      await page.goto(`${BASE}/governance?tab=ledger&entity=${itemId}`);
      await page.waitForSelector('[data-ready]');
      const event = page.locator('table tbody tr').filter({ hasText: 'Decision recorded' }).first();
      await event.waitFor();
      const text = (await event.textContent()) ?? '';
      assert(text.includes('Helen Strand'), 'the ledger names who decided');
      assert(text.includes('Reserve rights') && text.includes(reason), 'the ledger carries the decision and its reason');
      await page.getByRole('button', { name: 'Verify the chain' }).click();
      await page.locator('[data-chain-result]').getByText(/Chain intact: [\d,]+ events checked/).waitFor({ timeout: 60000 });
      await signOut(page);
    },
  },
];

const browser = await chromium.launch({ headless: !process.env.HEADED });
let failed = 0;
for (const journey of journeys) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const problems = [];
  page.on('pageerror', (error) => problems.push(String(error)));
  const started = Date.now();
  try {
    await journey.run(page);
    assert(problems.length === 0, `the page raised errors: ${problems.join(' | ')}`);
    console.log(`ok    ${journey.name} (${((Date.now() - started) / 1000).toFixed(1)}s)`);
  } catch (error) {
    failed += 1;
    mkdirSync(failuresDir, { recursive: true });
    const shot = resolve(failuresDir, `journey-${journeys.indexOf(journey) + 1}.png`);
    await page.screenshot({ path: shot }).catch(() => {});
    console.log(`FAIL  ${journey.name}\n      ${String(error.message ?? error).split('\n').slice(0, 6).join('\n      ')}\n      screenshot: ${shot}`);
  } finally {
    await context.close();
  }
}
await browser.close();
console.log(failed === 0 ? `PASSED: ${journeys.length} journeys` : `FAILED: ${failed} of ${journeys.length} journeys`);
process.exit(failed === 0 ? 0 : 1);
