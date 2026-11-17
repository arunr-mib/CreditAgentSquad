// Repair journeys against the running stack, with screenshots at device scale factor 2 in frontend/screenshots/repair-*.png.
//
// These need a database loaded by frontend/e2e/seed_repair.py (see its header): the normal seed holds no
// spread with figures waiting for a person. Journeys 1 and 2 record real corrections (1 also a decision)
// and assert what a first correction does, so they need a fresh load each time; 3, 4 and 5 can be repeated.
//
// Usage: node e2e/repair.mjs [--only 1,3]     (BASE_URL=http://localhost:5173 by default; HEADED=1 to watch)
// Uses the globally installed Playwright and the axe-core dev dependency; nothing is downloaded.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const ANALYST = 'priya.raman@bankofstoic.example';
const MANAGER = 'dana.whitfield@bankofstoic.example';
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

const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

/** axe-core (WCAG 2.1 A and AA, best practices) on one region: nothing critical or serious, contrast included. */
async function expectAccessible(page, selector, what) {
  await page.evaluate(axeSource);
  const result = await page.evaluate((target) => window.axe.run(target, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] } }), selector);
  const bad = result.violations.filter((violation) => violation.impact === 'critical' || violation.impact === 'serious');
  const lesser = result.violations.length - bad.length;
  console.log(`      axe on ${what}: ${result.passes.length} rules passed, ${bad.length} critical or serious, ${lesser} lesser`);
  assert(bad.length === 0, `${what} has accessibility violations: ${bad.map((violation) => `${violation.id} (${violation.nodes.length}): ${violation.nodes[0]?.html.slice(0, 120)}`).join('; ')}`);
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
      await expectAccessible(page, '[data-held-figures]', 'the held figures with a correction form open');
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
  {
    name: 'an analyst corrects a figure from the source drawer, sees a covenant outcome change, and the screen beneath shows the new figure; a calculated figure offers no correction',
    async run(page) {
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/borrowers/halvorsen-plastics/spreads`);
      await page.waitForSelector('[data-ready]');
      const line = page.locator('table tbody tr').filter({ hasText: 'Cash paid for income taxes' }).first();
      const cell = line.getByRole('button').last();
      const before = ((await cell.getAttribute('aria-label')) ?? '').split(', Cash paid')[0];
      await cell.click();
      const drawer = page.locator('[data-source-drawer]');
      await drawer.getByRole('heading', { name: 'Cash paid for income taxes' }).waitFor();
      await drawer.getByRole('button', { name: 'Reject this figure' }).waitFor();
      await expectFocusRing(page, drawer.getByRole('button', { name: 'Correct this figure' }), 'the Correct this figure button');
      await drawer.getByRole('button', { name: 'Correct this figure' }).click();
      const form = drawer.getByRole('form', { name: 'Correct Cash paid for income taxes' });
      const value = form.getByLabel('Value, in whole US dollars');
      const onFile = await value.inputValue();
      assert(/^\d+$/.test(onFile), `the form starts from the stored value, got ${onFile}`);
      // A reason is required before anything is sent.
      await form.getByRole('button', { name: 'Record the correction' }).click();
      await form.getByText('A reason is required. It is recorded in the ledger with your name.').waitFor();
      await expectAccessible(page, '[data-source-drawer]', 'the source drawer with a correction form open');
      const corrected = String(Number(onFile) * 4);
      await value.fill(corrected);
      await form.getByLabel('Reason (required)').fill('Journey: the notes page reports cash taxes paid for the nine months, not the quarter.');
      await form.getByRole('button', { name: 'Record the correction' }).click();

      const result = drawer.locator('[data-change-result="corrected"]');
      await result.getByText('Corrected. On file now:').waitFor();
      const note = result.locator('[data-recalculation]');
      await note.getByText(/\d+ results calculated from the old figure were retired\./).waitFor();
      await note.getByText('Statement totals were recalculated from the figures now on file, and the statements foot.').waitFor();
      await note.getByRole('listitem', { name: /^Fixed Charge Coverage Ratio, Q3 2026: Compliant → Breach/ }).waitFor();
      // The fact on show is now the superseded one, and it no longer offers a correction.
      await drawer.getByText('Superseded', { exact: true }).first().waitFor();
      assert((await drawer.getByRole('button', { name: 'Correct this figure' }).count()) === 0, 'a superseded figure offers no correction');
      await shot(page, 'repair-07-drawer-correction');

      // The grid beneath the drawer was read again: it shows the new figure, entered by a person.
      await drawer.getByRole('button', { name: 'Close the source' }).click();
      await drawer.waitFor({ state: 'detached' });
      const after = Number(corrected) / 1000;
      await line.getByRole('button', { name: new RegExp(`^${after.toLocaleString('en-US')}, Cash paid for income taxes, .*Entered by a person`) }).waitFor();
      assert(before !== after.toLocaleString('en-US'), 'the figure in the grid changed');

      // A calculated figure cannot be corrected; the drawer says where the correction belongs.
      await page.goto(`${BASE}/borrowers/halvorsen-plastics/covenants`);
      await page.waitForSelector('[data-ready]');
      const test = page.locator('table tbody tr[data-row]').filter({ hasText: 'Fixed Charge Coverage Ratio' }).first();
      await test.getByText(/Breach/).first().waitFor();
      await test.getByRole('button', { name: /Fixed Charge Coverage Ratio, .*Calculated by code/ }).first().click();
      await drawer.getByText('Calculated by code; correct the figure it was calculated from.', { exact: false }).waitFor();
      assert((await drawer.getByRole('button', { name: /Correct this figure|Reject this figure/ }).count()) === 0, 'a calculated figure offers neither correction nor rejection');
      await shot(page, 'repair-08-drawer-calculated-figure');
    },
  },
  {
    name: 'an analyst edits a section of commentary in place, inserts a figure by picking it from the review sheet, saves, and reads the server’s warnings; an unknown reference is refused',
    async run(page) {
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/review-room`);
      await page.waitForSelector('[data-ready]');
      await page.getByRole('button', { name: /Larkspur Environmental Services/ }).first().click();
      const sheet = page.locator('[data-review-sheet]');
      const summary = sheet.locator('[data-commentary-section="summary"]');
      await summary.getByRole('button', { name: 'Edit summary' }).click();
      const editor = summary.getByRole('form', { name: 'Edit summary' });
      const area = editor.getByRole('textbox');
      assert((await area.inputValue()).length > 0, 'the editor starts from the section as it stands');
      await expectKeyboardReachable(page, editor);
      await expectFocusRing(page, area, 'the commentary field');
      await area.fill('Leverage held steady over the period: total debt to EBITDA was ');

      // The figure is picked from the sheet, from the keyboard, not typed.
      await editor.getByRole('button', { name: 'Insert a figure' }).press('Enter');
      const find = page.getByRole('combobox', { name: 'Find a figure on this sheet' });
      await find.waitFor();
      assert(await find.evaluate((element) => element === document.activeElement), 'the picker’s search field takes focus');
      await find.pressSequentially('total debt ebitda 2026');
      const options = page.getByRole('option');
      assert((await options.count()) === 1, `one figure matches, got ${await options.count()}`);
      const picked = ((await options.first().locator('.tnum').textContent()) ?? '').trim();
      await shot(page, 'repair-09-commentary-insert-figure');
      await expectAccessible(page, '[data-commentary-editor]', 'the commentary editor');
      await expectAccessible(page, '[role="dialog"][aria-label="Figures on this review sheet"]', 'the figure picker');
      await find.press('Enter');
      await page.getByRole('combobox', { name: 'Find a figure on this sheet' }).waitFor({ state: 'detached' });
      assert(/was \{\{fact:[0-9a-f-]{36}\}\}$/.test(await area.inputValue()), `a reference was inserted at the caret, got: ${await area.inputValue()}`);
      assert(await area.evaluate((element) => element === document.activeElement), 'focus returns to the text after the figure is inserted');
      // The preview shows the stored figure, and it opens its source like any other.
      await editor.locator('[data-commentary-preview]').getByRole('button', { name: new RegExp(`^${picked.replace(/[.$]/g, '\\$&')}, `) }).waitFor();

      // A number typed by hand is allowed, and the server says so.
      await area.press('End');
      await area.pressSequentially(', against 2.5 times allowed.');
      await editor.getByRole('button', { name: 'Save as a draft' }).click();
      const saved = summary.locator('[data-commentary-saved="summary"]');
      await saved.getByText(/Summary saved as a draft, with \d+ warnings? from the server/).waitFor();
      assert((await saved.getByRole('listitem').count()) >= 1, 'the server’s warnings are listed');
      await summary.getByText(/Summary, version \d+ · Priya Raman/).waitFor();
      await summary.getByText('Draft, not yet approved').waitFor();
      await summary.getByRole('button', { name: new RegExp(`^${picked.replace(/[.$]/g, '\\$&')}, `) }).waitFor();
      // Approval stays where it was: the question for a second person is still beside the sheet.
      await page.locator('[data-work-item]').getByText('Commentary awaiting approval').waitFor();
      assert((await page.locator('[data-work-item]').getAttribute('data-item-status')) === 'open', 'saving does not approve the commentary');
      await shot(page, 'repair-10-commentary-saved-with-warnings');

      // A reference to a fact that does not exist is refused, in the server's words, and nothing is saved.
      await summary.getByRole('button', { name: 'Edit summary' }).click();
      const again = summary.getByRole('form', { name: 'Edit summary' });
      await again.getByRole('textbox').press('End');
      await again.getByRole('textbox').pressSequentially(' {{fact:00000000-0000-0000-0000-000000000000}}');
      await again.getByText(/unresolved 00000000/).waitFor();
      await again.getByRole('button', { name: 'Save as a draft' }).click();
      await again.getByRole('alert').getByText(/The server said: “/).waitFor();
      await again.getByRole('button', { name: 'Cancel' }).click();
      await summary.getByText(/Summary, version \d+ · Priya Raman/).waitFor();
    },
  },
  {
    name: 'an analyst files a PDF on the borrower’s documents tab; a file that is not a PDF is refused in the server’s words',
    async run(page) {
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/borrowers/larkspur-environmental/documents`);
      await page.waitForSelector('[data-ready]');
      const rows = page.locator('table tbody tr[data-row]');
      const before = await rows.count();
      await page.getByRole('button', { name: 'File a document' }).click();
      const form = page.getByRole('form', { name: 'File a document' });
      const file = form.getByLabel('PDF file');
      await expectKeyboardReachable(page, form);
      await expectFocusRing(page, file, 'the file field');

      // Nothing is sent without a file, and the field says why.
      await form.getByRole('button', { name: 'File the document' }).click();
      await form.getByText('Choose a PDF file first.').waitFor();
      assert((await file.getAttribute('aria-invalid')) === 'true', 'the empty file field is marked invalid');

      // The server is the judge of what a PDF is.
      await file.setInputFiles({ name: 'meeting-notes.pdf', mimeType: 'application/pdf', buffer: Buffer.from('These are notes typed into a text file, not a PDF.') });
      await form.getByRole('button', { name: 'File the document' }).click();
      await form.getByRole('alert').getByText('The server said: “Only PDF files are accepted.”').waitFor();
      assert((await rows.count()) === before, 'nothing was filed');

      const title = `Compliance certificate, resent ${new Date().toISOString().slice(0, 19)}`;
      await file.setInputFiles(resolve(here, '..', '..', 'synthetic', 'out', 'documents', 'larkspur-environmental', 'cc-2026-06-30.pdf'));
      await form.getByLabel('Title (optional)').fill(title);
      await form.getByRole('button', { name: 'File the document' }).click();
      const result = form.locator('[data-upload-result]');
      await result.getByText(`Filed: ${title}`).waitFor();
      await result.getByText(/pages?, read page by page, received \d{1,2} \w{3} \d{4}\. Unclassified until intake reads it\./).waitFor();
      assert((await form.getByRole('alert').count()) === 0, 'the earlier refusal is gone');
      // The list was read again: the document is on file, unclassified.
      const row = rows.filter({ hasText: title });
      await row.waitFor();
      await row.getByText('Unclassified').waitFor();
      await page.waitForFunction((expected) => document.querySelectorAll('table tbody tr[data-row]').length === expected, before + 1);
      await shot(page, 'repair-11-document-upload');
      await expectAccessible(page, '[data-upload-document]', 'the upload form with its result');
      await result.getByRole('link', { name: /Open it/ }).click();
      await page.waitForURL(/\/documents\/[0-9a-f-]+/);
      await page.locator('main [data-pdf-page="ready"]').waitFor({ timeout: 30000 });
    },
  },
  {
    name: 'a portfolio manager creates a package schedule where packages are listed and runs what is due; an analyst can read schedules but not create or run them',
    async run(page) {
      await signIn(page, MANAGER);
      await page.goto(`${BASE}/borrowers/larkspur-environmental/packages`);
      await page.waitForSelector('[data-ready]');
      const area = page.locator('[data-package-schedules]');
      const form = area.getByRole('form', { name: 'New package schedule' });
      await expectKeyboardReachable(page, area);
      await expectFocusRing(page, form.getByLabel('Title'), 'the schedule title field');

      // A schedule needs a title; the field says so and nothing is sent.
      await form.getByRole('button', { name: 'Create the schedule' }).click();
      await form.getByText('Give the schedule a title.').waitFor();
      assert((await form.getByLabel('Title').getAttribute('aria-invalid')) === 'true', 'the empty title is marked invalid');

      const title = `Quarterly review package ${new Date().toISOString().slice(11, 19)}`;
      await form.getByLabel('Title').fill(title);
      await form.getByLabel('Days after period end').fill('45');
      // 45 days after 30 Sep 2026: already due on the workspace's date, so running now prepares it.
      await form.getByLabel('First run (optional)').fill('2026-11-14');
      await form.getByRole('button', { name: 'Create the schedule' }).click();
      await form.locator('[data-schedule-created]').getByText(`Created: ${title}, first run 14 Nov 2026. It is in the ledger.`).waitFor();
      const row = area.locator('table tbody tr').filter({ hasText: title });
      await row.waitFor();
      const cells = (await row.locator('th, td').allTextContents()).map((text) => text.trim());
      assert(cells.join(' | ') === `${title} | This borrower | Quarterly | 45 days after period end | Word, Excel, PowerPoint | 14 Nov 2026`, `the schedule is listed as created, got: ${cells.join(' | ')}`);

      const packagesBefore = await page.locator('[data-package]').count();
      await area.getByRole('button', { name: 'Run schedules that are due' }).click();
      const report = area.locator('[data-schedule-run]');
      await report.getByText(new RegExp(`^${title}, Q3 2026: (a package was prepared, not released\\.|not generated\\. The server said: “)`)).waitFor({ timeout: 60000 });
      const said = ((await report.textContent()) ?? '').trim();
      console.log(`      the run reported: ${said}`);
      if (said.includes('a package was prepared')) {
        // The package appears in the list above, generated and not released; the schedule moved on to the next period.
        await page.waitForFunction((expected) => document.querySelectorAll('[data-package]').length === expected, packagesBefore + 1);
        await page.locator('[data-package]').first().getByText(/Generated, not released|Not released: commentary is a draft/).waitFor();
        await row.getByText('14 Feb 2027').waitFor();
      }
      await shot(page, 'repair-12-package-schedules');
      await expectAccessible(page, '[data-package-schedules]', 'the package schedules');

      // Running again on the same day generates nothing, and says so.
      await area.getByRole('button', { name: 'Run schedules that are due' }).click();
      if (said.includes('a package was prepared')) await report.getByText('No schedule was due on 17 Nov 2026. Nothing was generated.').waitFor();

      // An analyst can read the schedules but is offered neither control.
      await page.getByRole('button', { name: /Account menu/ }).click();
      await page.getByRole('menuitem', { name: 'Sign out' }).click();
      await page.waitForURL('**/sign-in**');
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/borrowers/larkspur-environmental/packages`);
      await page.waitForSelector('[data-ready]');
      await area.locator('table tbody tr').filter({ hasText: title }).waitFor();
      assert((await area.getByRole('button', { name: 'Run schedules that are due' }).count()) === 0, 'an analyst is not offered the run');
      assert((await area.getByRole('form', { name: 'New package schedule' }).count()) === 0, 'an analyst is not offered the form');
      await area.getByText(/Creating and running schedules needs a portfolio manager or a credit officer\. Your role, Credit analyst, can read them\./).waitFor();
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
