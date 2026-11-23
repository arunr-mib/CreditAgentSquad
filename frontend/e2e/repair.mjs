// Repair journeys against the running stack, with screenshots at device scale factor 2 in frontend/screenshots/repair-*.png.
//
// These need a database loaded by frontend/e2e/seed_repair.py (see its header): the normal seed holds no
// spread with figures waiting for a person. Journeys 1 and 2 record real corrections (1 also a decision)
// and assert what a first correction does, so they need a fresh load each time; 3, 4 and 5 can be repeated.
// Journey 1 is the held-figures panel: what is on file, what was read, why it was held, and one clear action.
//
// Journeys enter a held item through its client thread (`/clients/<code>?case=<id>`), the way Squad does.
//
// Usage: node e2e/repair.mjs [--only 1,3]     (BASE_URL=http://localhost:5173 by default; HEADED=1 to watch)
// Uses the globally installed Playwright and the axe-core dev dependency; nothing is downloaded.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { refuseFrozenHost } from './frozen-hosts.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
refuseFrozenHost(BASE); // a sign-in on a frozen site would append to its ledger
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const ANALYST = 'priya.raman@bankofstoic.example';
// Squad gives a client's open work to that client's analyst: Harrowgate's is Jules Hartmann.
const HARROWGATE_ANALYST = 'jules.hartmann@bankofstoic.example';
// An analyst acts only on her own clients (owner answer 9): Halvorsen Plastics is Naomi Castellano's.
const HALVORSEN_ANALYST = 'naomi.castellano@bankofstoic.example';
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
  await page.waitForURL(`${BASE}/`);
  await page.locator('.sq-main').waitFor();
}

/** Opens a client's open item of one type in its thread, focused, with its held figures showing. */
async function openHeld(page, code, itemType = 'spread.value_unverified') {
  const borrowers = await (await page.request.get(`${BASE}/api/v1/borrowers`)).json();
  const borrower = borrowers.find((b) => b.code === code);
  const items = await (await page.request.get(`${BASE}/api/v1/work-items?item_type=${itemType}&borrower_id=${borrower.id}`)).json();
  assert(items.length > 0, `an open ${itemType} for ${code} (load a fresh database with e2e/seed_repair.py)`);
  await page.goto(`${BASE}/clients/${code}?case=${items[0].id}`);
  const panel = page.locator(`[data-work-item="${items[0].id}"][data-focused="true"]`);
  await panel.locator('[data-held-figures]').waitFor();
  return { panel, itemId: items[0].id, borrower };
}

async function shot(page, name) {
  // Toasts are transient; let the page settle so a capture never catches one half drawn.
  await page.waitForTimeout(250);
  const file = resolve(shotsDir, `${name}.png`);
  await page.screenshot({ path: file });
  console.log(`      wrote ${file}`);
}

/** Scrolls so `locator` starts just under the top bar: a long panel is captured from the part the journey is about. */
async function bringToTop(page, locator) {
  await locator.evaluate((element) => {
    element.style.scrollMarginTop = '96px';
    element.scrollIntoView({ block: 'start' });
    element.style.scrollMarginTop = '';
  });
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
    name: 'an analyst opens a held spread, reads what is on file, what was read and why each figure was held, files two swapped readings with one action, enters two figures, sees what was recalculated and finishes the spread',
    async run(page) {
      await signIn(page, HARROWGATE_ANALYST);
      const { panel, itemId, borrower } = await openHeld(page, 'harrowgate-precision');
      const section = panel.locator('[data-held-figures]');
      const pair = section.locator('[data-swapped-pair]');
      const swap = pair.getByRole('button', { name: 'File both under the lines their labels name' });
      await swap.waitFor();

      const row = (key) => section.locator(`[data-held-row="${key}"]`);
      const printed = async (key) => ((await row(key).locator('[data-read] .tnum').first().textContent()) ?? '').trim();
      const part = async (key, name) => ((await row(key).locator(`[data-${name}]`).textContent()) ?? '').replace(/\s+/g, ' ').trim();
      assert((await section.locator('[data-held-row]').count()) === 4, 'four figures are held');
      assert((await section.locator('[data-held-count]').textContent()) === '4 of 4 still need a person', 'all four wait for a person');
      const payablePrinted = await printed('bs.accrued_liabilities'); // the Accounts payable row, filed under accrued liabilities
      const accruedPrinted = await printed('bs.accounts_payable');

      // Each held figure says three things, in this order: what is on file, what was read from the document, why it was held.
      for (const key of ['bs.inventory', 'bs.accrued_liabilities', 'bs.accounts_payable', 'is.interest_expense']) {
        const terms = (await row(key).locator('dt').allTextContents()).slice(0, 3);
        assert(terms.join(' | ') === 'On file | Read from the document | Why it was held', `the row for ${key} is labelled in order, got: ${terms.join(' | ')}`);
      }
      // On file: the line the figure was filed under and the value stored for it, held until a person decides.
      const onFile = await part('bs.accrued_liabilities', 'on-file');
      assert(onFile.startsWith(`Accrued liabilities$${payablePrinted},000`) && onFile.includes('held: not used in any calculation until a person decides'), `what is on file is said, got: ${onFile}`);
      await row('bs.accrued_liabilities').locator('[data-on-file]').getByRole('button', { name: new RegExp(`^\\$${payablePrinted},000, Accrued liabilities, `) }).waitFor();
      assert((await part('bs.inventory', 'on-file')).startsWith('InventoryNothing on file'), 'a figure that was not stored says nothing is on file');
      // Read from the document: the label as printed, the figure as printed, and the link that opens the page.
      const read = await part('bs.accrued_liabilities', 'read');
      assert(read.startsWith(`“Accounts payable”${payablePrinted}as printed, in thousands`), `what was read is said as printed, got: ${read}`);
      assert((await row('bs.accrued_liabilities').getByRole('button', { name: 'Open page 2' }).count()) === 1, 'the reading links to its page');
      // Why it was held: the check's reason in plain words, with lines named as the screen names them.
      const why = await part('bs.accrued_liabilities', 'why');
      assert(why === 'The row is printed “Accounts payable”, which names Accounts payable, not Accrued liabilities, the line it was filed under.', `the reason is in plain words, got: ${why}`);
      assert((await part('is.interest_expense', 'why')) === 'The figure the reader reported is not on the page it cited. Nothing was stored.', 'a figure that is not on the page says so');

      // The two swapped readings are named once, with one action for both; every other held figure has one action of its own.
      const finding = ((await pair.locator('p').first().textContent()) ?? '').replace(/\s+/g, ' ').trim();
      assert(
        finding === 'Two readings look swapped. The row printed “Accounts payable” was filed under Accrued liabilities, and the row printed “Accrued liabilities” under Accounts payable.',
        `the swap is said in one sentence, got: ${finding}`,
      );
      const willDo = ((await pair.locator('[data-will-do]').textContent()) ?? '').replace(/\s+/g, ' ').trim();
      assert(
        /^Stores each figure under the line its printed label names, as two corrections in your name\. .*totals will be footed and this period’s covenants tested once the decision below is recorded\.$/.test(willDo),
        `the action says what it will do before the click, got: ${willDo}`,
      );
      const primaries = (await section.locator('[data-primary]').allTextContents()).map((label) => label.trim());
      assert(primaries.join(' | ') === 'File both under the lines their labels name | Enter the figure | Enter the figure', `one primary action per held figure, got: ${primaries.join(' | ')}`);
      for (const key of ['bs.accrued_liabilities', 'bs.accounts_payable']) {
        assert((await row(key).locator('[data-primary]').count()) === 0, 'a figure covered by the pair’s action has no primary of its own');
        const choices = (await row(key).locator('[data-actions] button').allTextContents()).map((label) => label.trim());
        assert(choices.join(' | ') === 'Keep as read | Enter a different figure | Reject this reading', `the other choices are offered beside it, got: ${choices.join(' | ')}`);
      }
      assert((await row('bs.inventory').locator('[data-actions] button').count()) === 1, 'a figure with no stored value can only be entered');
      assert((await section.getByRole('button', { name: /^Confirm|^Correct/ }).count()) === 0, 'no Confirm or Correct button is left');
      await expectKeyboardReachable(page, section);
      await expectFocusRing(page, swap, 'the action for the swapped pair');
      await swap.blur();
      await bringToTop(page, section);
      await shot(page, 'repair-01-held-figures');

      // Each held figure opens the page it was read from.
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
      assert((await panel.locator('[data-case]').getAttribute('data-item-status')) === 'open', 'the item is still open after the refusal');

      // Another choice: a different figure. The form checks the value and the reason before anything is sent.
      await row('bs.accrued_liabilities').getByRole('button', { name: 'Enter a different figure for Accrued liabilities' }).click();
      let form = row('bs.accrued_liabilities').getByRole('form', { name: 'Enter a different figure for Accrued liabilities' });
      const value = form.getByLabel('Value, in whole US dollars');
      assert((await value.inputValue()) === dollars(payablePrinted), 'the form starts from the value on file');
      assert(await value.evaluate((element) => element === document.activeElement), 'the value field takes focus when the form opens');
      await value.fill('about two million');
      await form.getByRole('button', { name: 'Record the figure' }).click();
      await form.getByText('This is not a number. Enter digits only, for example 1236000.').waitFor();
      await form.getByText('A reason is required. It is recorded in the ledger with your name.').waitFor();
      assert((await value.getAttribute('aria-invalid')) === 'true', 'the invalid value is marked for assistive technology');
      const described = await value.getAttribute('aria-describedby');
      assert(described && (await page.locator(`[id="${described}"]`).textContent())?.startsWith('This is not a number'), 'the error is tied to its field');
      await shot(page, 'repair-03-different-figure-form-errors');
      await expectAccessible(page, '[data-held-figures]', 'the held figures with a form open');
      await value.fill(dollars(accruedPrinted));
      await form.getByText(`shown on a statement in thousands as ${accruedPrinted}.`).waitFor();
      await form.getByRole('button', { name: 'Cancel' }).click();
      await form.waitFor({ state: 'detached' });

      // One action files both readings under the lines their labels name, as two corrections, from the keyboard;
      // the panel then says what code did for each.
      await swap.press('Enter');
      await pair.getByText('Both filed under the lines their labels name').waitFor();
      const notes = pair.locator('[data-recalculation]');
      await notes.nth(0).getByText('What code recalculated when Accrued liabilities was corrected').waitFor();
      await notes.nth(1).getByText('What code recalculated when Accounts payable was corrected').waitFor();
      for (const index of [0, 1]) {
        const said = (await notes.nth(index).textContent()) ?? '';
        assert(/retired|Nothing had been calculated/.test(said), `the result says what was recalculated, got: ${said}`);
      }
      assert((await swap.count()) === 0, 'the pair’s action is not offered twice');
      // Each line now has the figure whose label names it, entered by a person, and neither waits any longer.
      await row('bs.accrued_liabilities').locator('[data-on-file]').getByRole('button', { name: new RegExp(`^\\$${accruedPrinted},000, Accrued liabilities, .*Entered by a person`) }).waitFor();
      await row('bs.accounts_payable').locator('[data-on-file]').getByRole('button', { name: new RegExp(`^\\$${payablePrinted},000, Accounts payable, .*Entered by a person`) }).waitFor();
      await row('bs.accrued_liabilities').getByText('Cleared: a person entered the figure on file').waitFor();
      await section.getByText('2 of 4 still need a person').waitFor();
      assert((await section.locator('[data-primary]').count()) === 2, 'only the two figures still waiting have a primary action');
      await bringToTop(page, section);
      await shot(page, 'repair-04-swapped-pair-filed');
      await expectAccessible(page, '[data-held-figures]', 'the held figures after the pair was filed');

      // Enter the two figures the spread could not store.
      await row('bs.inventory').getByRole('button', { name: 'Enter the figure for Inventory' }).click();
      form = row('bs.inventory').getByRole('form', { name: /^Enter Inventory, at / });
      await form.getByLabel('Value, in whole US dollars').fill(dollars(await printed('bs.inventory')));
      await form.getByLabel('Reason (required)').fill('Page 2: the row is printed as Inventory; the figure is as reported.');
      await form.getByRole('button', { name: 'Record the figure' }).click();
      await section.getByText('1 of 4 still needs a person').waitFor();

      await row('is.interest_expense').getByRole('button', { name: 'Enter the figure for Interest expense' }).click();
      form = row('is.interest_expense').getByRole('form', { name: /^Enter Interest expense, 9 months to / });
      // The reader misreported the last digit; the page prints one less.
      await form.getByLabel('Value, in whole US dollars').fill(dollars(await printed('is.interest_expense'), -1));
      await form.getByLabel('Reason (required)').fill('Page 3: read from the interest expense row by hand.');
      await form.getByRole('button', { name: 'Record the figure' }).click();
      await section.getByText('All 4 cleared; record the decision below').waitFor();
      await bringToTop(page, section);
      await shot(page, 'repair-05-all-cleared');

      // The decision that finishes the spread stays with the person.
      await panel.getByRole('radio', { name: /Values corrected/ }).check();
      await panel.getByRole('form', { name: 'Record a decision' }).getByLabel(/Reason/).fill('Two rows were filed under each other’s lines and two figures were entered from the page.');
      await panel.getByRole('button', { name: 'Record decision' }).click();
      await page.waitForFunction((id) => document.querySelector(`[data-case="${id}"]`)?.getAttribute('data-item-status') === 'decided', itemId);
      // The held spread is decided and no new question was raised, so the corrected statements foot.
      const open = await (await page.request.get(`${BASE}/api/v1/work-items?item_type=spread.does_not_foot&borrower_id=${borrower.id}`)).json();
      assert(open.length === 0, 'no new does-not-foot question was raised for the borrower');
      const stillHeld = await (await page.request.get(`${BASE}/api/v1/work-items?item_type=spread.value_unverified&borrower_id=${borrower.id}`)).json();
      assert(stillHeld.length === 0, 'the held spread is no longer open');
      await shot(page, 'repair-06-decision-recorded');

      // The corrected figure is what the spread grid now shows, entered by a person.
      await page.goto(`${BASE}/clients/harrowgate-precision/file/spreads`);
      await page.locator('.sq-file[data-ready]').waitFor();
      const line = page.locator('table tbody tr').filter({ hasText: 'Accrued liabilities' }).first();
      await line.getByRole('button', { name: new RegExp(`^\\$${accruedPrinted},000, Accrued liabilities, .*Entered by a person`) }).waitFor(); // the client file shows whole dollars
    },
  },
  {
    name: 'an analyst corrects a figure from the source drawer, sees a covenant outcome change, and the screen beneath shows the new figure; a calculated figure offers no correction',
    async run(page) {
      await signIn(page, HALVORSEN_ANALYST);
      await page.goto(`${BASE}/clients/halvorsen-plastics/file/spreads`);
      await page.locator('.sq-file[data-ready]').waitFor();
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
      const after = `$${Number(corrected).toLocaleString('en-US')}`; // the client file shows whole dollars
      await line.getByRole('button', { name: new RegExp(`^\\${after}, Cash paid for income taxes, .*Entered by a person`) }).waitFor();
      assert(before !== after, 'the figure in the grid changed');

      // A calculated figure cannot be corrected; the drawer says where the correction belongs.
      await page.goto(`${BASE}/clients/halvorsen-plastics/file/covenants`);
      await page.locator('.sq-file[data-ready]').waitFor();
      const test = page.locator('table[aria-label="Covenants"] tbody tr').filter({ hasText: 'Fixed Charge Coverage Ratio' }).first();
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
      // The sheet's labels carry the period ("Total debt to EBITDA, Sep 30, 2026", beside the same ratio a year earlier
      // and the leverage covenant's own rows), so the search names the whole label and the option is found by it.
      const LABEL = 'Total debt to EBITDA, Sep 30, 2026';
      await find.pressSequentially(LABEL);
      // The figures listbox only: the review room's route form has <option> elements of its own.
      const options = page.getByRole('listbox', { name: 'Figures on this review sheet' }).getByRole('option');
      assert((await options.count()) === 1, `one figure matches ${LABEL}, got ${await options.count()}: ${(await options.allTextContents()).join(' | ')}`);
      assert(((await options.first().locator('span').first().textContent()) ?? '').trim() === LABEL, 'the one match is the label asked for');
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
      await page.locator('[data-work-item] [data-case]').waitFor();
      assert((await page.locator('[data-work-item] [data-case]').getAttribute('data-item-status')) === 'open', 'saving does not approve the commentary');
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
    name: 'a portfolio manager approves the commentary in the review room, prepares the package, verifies every figure and releases it',
    async run(page) {
      await signIn(page, MANAGER);
      await page.goto(`${BASE}/review-room`);
      await page.waitForSelector('[data-ready]');
      await page.getByRole('button', { name: /Larkspur Environmental Services/ }).first().click();
      const sheetId = await page.locator('[data-review-sheet]').getAttribute('data-review-sheet');
      const approval = page.getByRole('complementary', { name: 'Approval of this commentary' });
      await approval.locator('[data-case]').waitFor();
      const itemId = await approval.getAttribute('data-work-item');
      // Dana writes the summary herself: as its last editor she is refused, and the case does not offer her Approve.
      const write = (who, body) => who.request.post(`${BASE}/api/v1/review-sheets/${sheetId}/commentary`, { data: { section: 'summary', body } });
      assert((await write(page, 'The quarter was steady and nothing changed in the outlook.')).ok(), 'the manager’s summary was not saved');
      await page.reload();
      await page.getByRole('button', { name: /Larkspur Environmental Services/ }).first().click();
      await approval.locator('[data-case]').waitFor();
      assert((await approval.getByRole('radio', { name: /^Approve/ }).count()) === 0, 'the last editor was offered Approve');
      const refused = await page.request.post(`${BASE}/api/v1/work-items/${itemId}/decide`, { data: { decision: 'approve', reason: '' } });
      assert(refused.status() === 409 && /last edited the summary section/.test(await refused.text()), 'the server did not refuse the last editor');
      // Priya rewrites the summary, so Dana is a second person for it.
      const other = await page.context().browser().newContext();
      const priya = await other.newPage();
      await signIn(priya, ANALYST);
      assert((await write(priya, 'The quarter was steady; the outlook is unchanged.')).ok(), 'the analyst’s summary was not saved');
      await other.close();
      await page.reload();
      await page.getByRole('button', { name: /Larkspur Environmental Services/ }).first().click();
      await approval.getByRole('radio', { name: /^Approve/ }).check();
      await approval.getByRole('button', { name: 'Record decision' }).click();
      // what the person sees: the sheet reads as reviewed without a reload
      await page.locator('[data-review-sheet]').getByText(/^Reviewed by /).first().waitFor();
      await page.goto(`${BASE}/clients/larkspur-environmental/file/packages`);
      await page.locator('.sq-file [data-ready]').waitFor(); // the packages list itself has loaded, not only the client file around it
      const before = await page.locator('[data-package]').count();
      await page.getByRole('button', { name: 'Prepare the package' }).click();
      await page.waitForFunction((n) => document.querySelectorAll('[data-package]').length === n, before + 1);
      const card = page.locator('[data-package]').first();
      await card.getByRole('button', { name: 'Verify the files' }).click();
      await card.locator('[data-verify-result]').getByText(/Verified: all .* figures in the files trace to the snapshot/).waitFor();
      await card.getByRole('button', { name: 'Release' }).click();
      await card.getByText(/^Released/).waitFor();
      const id = await card.getAttribute('data-package');
      const pkg = await (await page.request.get(`${BASE}/api/v1/packages/${id}`)).json();
      assert(pkg.status === 'released', 'the package was not released on the server');
    },
  },
  {
    name: 'an analyst files a PDF in the client file’s documents view; a file that is not a PDF is refused in the server’s words',
    async run(page) {
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/clients/larkspur-environmental/file/documents`);
      await page.locator('.sq-file[data-ready]').waitFor();
      await page.getByRole('table', { name: 'Documents' }).waitFor();
      const rows = page.locator('table[aria-label="Documents"] tbody tr');
      const before = await rows.count();
      await page.getByRole('button', { name: 'File a document' }).click();
      const form = page.getByRole('form', { name: 'File a document' });
      const file = form.getByLabel('Document file');
      await expectKeyboardReachable(page, form);
      await expectFocusRing(page, file, 'the file field');

      // Nothing is sent without a file, and the field says why.
      await form.getByRole('button', { name: 'File the document' }).click();
      await form.getByText('Choose a document file first.').waitFor();
      assert((await file.getAttribute('aria-invalid')) === 'true', 'the empty file field is marked invalid');

      // The server is the judge of what a PDF is.
      await file.setInputFiles({ name: 'meeting-notes.pdf', mimeType: 'application/pdf', buffer: Buffer.from('These are notes typed into a text file, not a PDF.') });
      await form.getByRole('button', { name: 'File the document' }).click();
      await form.getByRole('alert').getByText('The server said: “Only PDF, Excel (.xlsx) and CSV files are accepted.”').waitFor();
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
      await row.getByText('Not yet classified').waitFor();
      await page.waitForFunction((expected) => document.querySelectorAll('table[aria-label="Documents"] tbody tr').length === expected, before + 1);
      await shot(page, 'repair-11-document-upload');
      await expectAccessible(page, '[data-upload-document]', 'the upload form with its result');
      await result.getByRole('link', { name: /Open it/ }).click();
      await page.waitForURL(/\/clients\/larkspur-environmental\/file\/documents\?document=[0-9a-f-]+/);
      await page.locator('[data-source-drawer] [data-pdf-page="ready"]').first().waitFor({ timeout: 30000 });
    },
  },
  {
    name: 'a portfolio manager creates a package schedule where packages are listed and runs what is due; an analyst can read schedules but not create or run them',
    async run(page) {
      await signIn(page, MANAGER);
      await page.goto(`${BASE}/clients/larkspur-environmental/file/packages`);
      await page.locator('.sq-file [data-ready]').waitFor(); // the packages list itself has loaded, not only the client file around it
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
      assert(cells.join(' | ') === `${title} | This client | Quarterly | 45 days after period end | Word, Excel, PowerPoint | 14 Nov 2026`, `the schedule is listed as created, got: ${cells.join(' | ')}`);

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
      await page.getByRole('button', { name: 'Sign out' }).click();
      await page.waitForURL('**/sign-in**');
      await signIn(page, ANALYST);
      await page.goto(`${BASE}/clients/larkspur-environmental/file/packages`);
      await page.locator('.sq-file [data-ready]').waitFor(); // the packages list itself has loaded, not only the client file around it
      await area.locator('table tbody tr').filter({ hasText: title }).waitFor();
      assert((await area.getByRole('button', { name: 'Run schedules that are due' }).count()) === 0, 'an analyst is not offered the run');
      assert((await area.getByRole('form', { name: 'New package schedule' }).count()) === 0, 'an analyst is not offered the form');
      await area.getByText('Your role can read package schedules but cannot create or run them; the server decides who may.').waitFor();
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
