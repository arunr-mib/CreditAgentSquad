// Repair journeys against the running stack, with screenshots at device scale factor 2 in frontend/screenshots/repair-*.png.
//
// These need a database loaded by frontend/e2e/seed_repair.py (see its header): the normal seed holds no
// spread with figures waiting for a person. The first journey records real corrections and a decision, so
// it needs a fresh load each time; the others can be repeated.
//
// Usage: node e2e/repair.mjs [--only 1,3]     (BASE_URL=http://localhost:5173 by default; HEADED=1 to watch)
// Uses the globally installed Playwright; nothing is downloaded.
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const ANALYST = 'priya.raman@bankofstoic.example';
const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = resolve(here, '..', 'screenshots');
const failuresDir = resolve(here, 'failures');
mkdirSync(shotsDir, { recursive: true });

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

async function shot(page, name) {
  // Toasts are transient; let the page settle so a capture never catches one half drawn.
  await page.waitForTimeout(250);
  const file = resolve(shotsDir, `${name}.png`);
  await page.screenshot({ path: file });
  console.log(`      wrote ${file}`);
}

/** "8,067" printed in thousands → "8067000" in whole dollars. */
const dollars = (printed, adjust = 0) => String((Number(printed.replace(/,/g, '')) + adjust) * 1000);

/** Every interactive control inside `scope` can take focus from the keyboard and shows the focus ring. */
async function expectKeyboardReachable(page, scope) {
  const problems = await scope.evaluate((root) => {
    const out = [];
    for (const control of root.querySelectorAll('button, a[href], input, textarea, select, [role="combobox"]')) {
      if (control.disabled || control.getAttribute('aria-hidden') === 'true') continue;
      if (control.tabIndex < 0) out.push(`not in the tab order: ${control.getAttribute('aria-label') ?? control.textContent?.trim().slice(0, 40)}`);
    }
    return out;
  });
  assert(problems.length === 0, `controls a keyboard cannot reach: ${problems.join('; ')}`);
}

async function expectFocusRing(page, locator, what) {
  await locator.focus();
  // :focus-visible applies after keyboard input; a Shift key press marks the modality without moving focus.
  await page.keyboard.press('Shift');
  const ring = await locator.evaluate((element) => {
    const own = getComputedStyle(element);
    const wrapper = element.closest('.focus-within\\:outline-2');
    const wrapped = wrapper ? getComputedStyle(wrapper) : null;
    return { own: own.outlineStyle !== 'none' && Number.parseFloat(own.outlineWidth) >= 2, wrapped: Boolean(wrapped) && wrapped.outlineStyle !== 'none' && Number.parseFloat(wrapped.outlineWidth) >= 2 };
  });
  assert(ring.own || ring.wrapped, `${what} shows a focus ring when focused from the keyboard`);
}

const journeys = [
  {
    name: 'an analyst opens a held spread, opens a held figure’s page, corrects two figures, keys two, sees what was recalculated and finishes the spread',
    async run(page) {
      await signIn(page, ANALYST);
      const rows = page.locator('table tbody tr[data-row]');
      const held = rows.filter({ hasText: 'could not be verified on the page' });
      assert((await held.count()) > 0, 'an open held spread is in the queue (load a fresh database with e2e/seed_repair.py)');
      const before = await rows.count();
      await held.first().click();
      const panel = page.locator('[data-work-item]');
      const section = panel.locator('[data-held-figures]');
      await section.getByRole('button', { name: /^Confirm / }).first().waitFor();
      const itemId = await panel.getAttribute('data-work-item');

      const row = (key) => section.locator(`[data-held-row="${key}"]`);
      const printed = async (key) => ((await row(key).locator('.tnum').first().textContent()) ?? '').trim();
      assert((await section.locator('[data-held-row]').count()) === 4, 'four figures are held');
      assert((await section.locator('[data-held-count]').textContent()) === '4 of 4 still need a person', 'all four wait for a person');
      // What was stored is offered for confirmation or correction; what was not stored can only be keyed.
      assert((await row('bs.accrued_liabilities').getByRole('button', { name: /^Confirm / }).count()) === 1, 'a stored figure can be confirmed');
      assert((await row('bs.inventory').getByRole('button', { name: /^Confirm |^Correct / }).count()) === 0, 'a figure with no stored value cannot be confirmed');
      assert((await row('bs.inventory').getByRole('button', { name: /^Key a figure/ }).count()) === 1, 'a figure with no stored value can be keyed');
      await expectKeyboardReachable(page, section);
      await expectFocusRing(page, row('bs.accrued_liabilities').getByRole('button', { name: /^Correct / }), 'the Correct button');
      await shot(page, 'repair-01-held-figures');

      // Each held figure opens the page it was read from.
      const payablePrinted = await printed('bs.accrued_liabilities'); // the Accounts payable row, filed under accrued liabilities
      const accruedPrinted = await printed('bs.accounts_payable');
      await row('bs.accrued_liabilities').locator('[data-printed-figure]').click();
      const drawer = page.locator('[data-source-drawer]');
      await drawer.getByRole('heading', { name: 'Accrued liabilities' }).waitFor();
      await drawer.locator('[data-pdf-page="ready"]').first().waitFor({ timeout: 30000 });
      await drawer.locator('[data-mark][data-active]').first().waitFor();
      await drawer.getByText('Proposed, not verified').waitFor();
      await shot(page, 'repair-02-held-figure-source');
      await drawer.getByRole('button', { name: 'Close the source' }).click();
      await drawer.waitFor({ state: 'detached' });

      // A decision the server cannot carry out is refused in its own words, and nothing is recorded.
      await panel.getByRole('radio', { name: /Values confirmed/ }).check();
      await panel.getByRole('button', { name: 'Record decision' }).click();
      await panel.getByText(/The server said: “these figures were not found on the page and have no value to confirm; enter them first/).waitFor();
      assert((await panel.getAttribute('data-item-status')) === 'open', 'the item is still open after the refusal');

      // Correct the figure filed under the wrong line. The form checks the value and the reason before anything is sent.
      await row('bs.accrued_liabilities').getByRole('button', { name: /^Correct / }).click();
      let form = row('bs.accrued_liabilities').getByRole('form', { name: 'Correct Accrued liabilities' });
      const value = form.getByLabel('Value, in whole US dollars');
      assert((await value.inputValue()) === dollars(payablePrinted), 'the form starts from the value on file');
      assert(await value.evaluate((element) => element === document.activeElement), 'the value field takes focus when the form opens');
      await value.fill('about two million');
      await form.getByRole('button', { name: 'Record the correction' }).click();
      await form.getByText('This is not a number. Enter digits only, for example 1236000.').waitFor();
      await form.getByText('A reason is required. It is recorded in the ledger with your name.').waitFor();
      assert((await value.getAttribute('aria-invalid')) === 'true', 'the invalid value is marked for assistive technology');
      const described = await value.getAttribute('aria-describedby');
      assert(described && (await page.locator(`[id="${described}"]`).textContent())?.startsWith('This is not a number'), 'the error is tied to its field');
      await shot(page, 'repair-03-correction-form-errors');
      await value.fill(dollars(accruedPrinted));
      await form.getByText(`shown on a statement in thousands as ${accruedPrinted}.`).waitFor();
      await form.getByLabel('Reason (required)').fill('Page 2: this is the accounts payable row. Accrued liabilities is the row beneath it.');
      // Enter in the value field submits, so the whole correction can be made from the keyboard.
      await value.press('Enter');
      const note = row('bs.accrued_liabilities').locator('[data-recalculation]');
      await note.getByText('What code recalculated').waitFor();
      const said = (await note.textContent()) ?? '';
      assert(/retired|Nothing had been calculated/.test(said), `the result says what was recalculated, got: ${said}`);
      await row('bs.accrued_liabilities').getByText('Entered by a person. On file now:').waitFor();
      await row('bs.accrued_liabilities').getByRole('button', { name: new RegExp(`^\\$${accruedPrinted},000, Accrued liabilities`) }).waitFor();
      await section.getByText('3 of 4 still need a person').waitFor();
      await shot(page, 'repair-04-corrected-and-recalculated');

      await row('bs.accounts_payable').getByRole('button', { name: /^Correct / }).click();
      form = row('bs.accounts_payable').getByRole('form', { name: 'Correct Accounts payable' });
      await form.getByLabel('Value, in whole US dollars').fill(dollars(payablePrinted));
      await form.getByLabel('Reason (required)').fill('Page 2: this is the accrued liabilities row. Accounts payable is the row above it.');
      await form.getByRole('button', { name: 'Record the correction' }).click();
      await section.getByText('2 of 4 still need a person').waitFor();

      // Key the two figures the spread could not store.
      await row('bs.inventory').getByRole('button', { name: /^Key a figure/ }).click();
      form = row('bs.inventory').getByRole('form', { name: /^Key Inventory/ });
      await form.getByLabel('Value, in whole US dollars').fill(dollars(await printed('bs.inventory')));
      await form.getByLabel('Reason (required)').fill('Page 2: the row is printed as Inventory; the figure is as reported.');
      await form.getByRole('button', { name: 'Record the figure' }).click();
      await section.getByText('1 of 4 still needs a person').waitFor();

      await row('is.interest_expense').getByRole('button', { name: /^Key a figure/ }).click();
      form = row('is.interest_expense').getByRole('form', { name: /^Key Interest expense/ });
      // The reader misreported the last digit; the page prints one less.
      await form.getByLabel('Value, in whole US dollars').fill(dollars(await printed('is.interest_expense'), -1));
      await form.getByLabel('Reason (required)').fill('Page 3: read from the interest expense row by hand.');
      await form.getByRole('button', { name: 'Record the figure' }).click();
      await section.getByText('All 4 cleared; record the decision below').waitFor();
      await shot(page, 'repair-05-all-cleared');

      // The decision that finishes the spread stays with the person.
      await panel.getByRole('radio', { name: /Values corrected/ }).check();
      await panel.getByRole('form', { name: 'Record a decision' }).getByLabel(/Reason/).fill('Two rows were filed under each other’s lines and two figures were keyed from the page.');
      await panel.getByRole('button', { name: 'Record decision' }).click();
      await page.getByText('Recorded: Values corrected').first().waitFor();
      await page.waitForFunction((id) => !document.querySelector(`[data-work-item="${id}"][data-item-status="open"]`), itemId);
      // One item fewer: the held spread left the queue and no new question was raised, so the corrected statements foot.
      await page.waitForFunction((expected) => document.querySelectorAll('table tbody tr[data-row]').length === expected, before - 1);
      assert((await rows.filter({ hasText: 'could not be verified on the page' }).count()) === 0, 'the held spread left the queue');
      await shot(page, 'repair-06-decision-recorded');

      // The corrected figure is what the spread grid now shows, entered by a person.
      await page.goto(`${BASE}/borrowers/harrowgate-precision/spreads`);
      await page.waitForSelector('[data-ready]');
      const line = page.locator('table tbody tr').filter({ hasText: 'Accrued liabilities' }).first();
      await line.getByRole('button', { name: new RegExp(`^${accruedPrinted}, Accrued liabilities, .*Entered by a person`) }).waitFor();
    },
  },
];

const onlyIndex = process.argv.indexOf('--only');
const only = onlyIndex > -1 ? (process.argv[onlyIndex + 1] ?? '').split(',').map(Number) : null;
const chosen = journeys.filter((_, index) => !only || only.includes(index + 1));

const browser = await chromium.launch({ headless: !process.env.HEADED });
let failed = 0;
for (const journey of chosen) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 2, reducedMotion: 'reduce' });
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
    const file = resolve(failuresDir, `repair-${journeys.indexOf(journey) + 1}.png`);
    await page.screenshot({ path: file }).catch(() => {});
    console.log(`FAIL  ${journey.name}\n      ${String(error.message ?? error).split('\n').slice(0, 8).join('\n      ')}\n      screenshot: ${file}`);
  } finally {
    await context.close();
  }
}
await browser.close();
console.log(failed === 0 ? `PASSED: ${chosen.length} ${chosen.length === 1 ? 'journey' : 'journeys'}` : `FAILED: ${failed} of ${chosen.length} journeys`);
process.exit(failed === 0 ? 0 : 1);
