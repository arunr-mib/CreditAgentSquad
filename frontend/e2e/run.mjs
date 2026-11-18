// End-to-end journeys against the running, seeded stack (API on 8000, workspace on 5173), written for
// the cockpit interface (docs/specs/2026-11-18-cockpit-design.md): one workspace drawer for the
// selected exception and the Copilot, an authority gate, the source drawer beside the page.
//
// Usage: pnpm e2e [--only 1,3]      (BASE_URL=http://localhost:5173 by default; HEADED=1 to watch)
// Uses the globally installed Playwright and the axe-core dev dependency; nothing is downloaded.
// No model is called: the Copilot and "Run … now" are checked only in their "off, with the reason" state.
//
// What a run changes in the database it points at:
// - the analyst journey routes one open covenant breach to a credit officer (an assignment, recorded in the ledger);
// - the officer journey records a decision on one open covenant breach, so each run takes one out of the queue.
//   A freshly seeded book has four; reseed the dev database when they are used up;
// - the four-eyes journey boards a proposed terms version through the API (there is no screen for boarding terms),
//   is refused when the same person approves it, then a second person rejects it, so nothing is left open.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const ANALYST = 'priya.raman@bankofstoic.example';
const OFFICER = 'helen.strand@bankofstoic.example';
const CREDIT_ADMIN = 'li.zhang@bankofstoic.example';
const BORROWER = 'kestrel-bay-packaging';
const BREACH = /is in breach|fails but the certificate reports compliance/;
const WIDTHS = [360, 390, 820, 1024, 1280, 1440];
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

const queueRows = (page) => page.locator('section[aria-label="Exception queue"] table tbody tr[data-row]');
const workspace = (page) => page.locator('[data-drawer]');

/** The workspace drawer is open on its first tab, showing the item with this id (or any item). */
async function expectItemInDrawer(page, itemId) {
  const drawer = workspace(page);
  await drawer.waitFor();
  const tab = drawer.getByRole('tab', { name: /Exception & decision/ });
  assert((await tab.getAttribute('aria-selected')) === 'true', 'the drawer opens on "Exception & decision"');
  const panel = drawer.locator(itemId ? `[data-work-item="${itemId}"]` : '[data-work-item]');
  await panel.waitFor();
  return panel;
}

/** The source drawer shows the rendered page with the cited figure outlined inside the page. */
async function expectHighlightedPage(page, printed) {
  const drawer = page.locator('[data-source-drawer]');
  await drawer.locator('[data-pdf-page="ready"]').first().waitFor({ timeout: 30000 });
  const mark = drawer.locator('[data-mark][data-active]').first();
  await mark.waitFor();
  const [markBox, pageBox] = await Promise.all([mark.boundingBox(), drawer.locator('[data-pdf-page="ready"] canvas').first().boundingBox()]);
  assert(markBox && pageBox, 'the highlight and the page are both drawn');
  assert(markBox.x >= pageBox.x - 4 && markBox.x + markBox.width <= pageBox.x + pageBox.width + 4, 'the highlight sits inside the page, left to right');
  assert(markBox.width > 8 && markBox.height > 4, 'the highlight has a real size');
  if (printed) {
    const quote = await drawer.locator('blockquote mark').first().textContent();
    assert(quote && quote.includes(printed), `the quoted figure is ${printed}, got ${quote}`);
  }
  // The canvas has ink on it: the PDF really rendered.
  const inked = await drawer.locator('[data-pdf-page="ready"] canvas').first().evaluate((canvas) => {
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let dark = 0;
    for (let i = 0; i < data.length; i += 40) if (data[i] < 120 && data[i + 3] > 0) dark += 1;
    return dark;
  });
  assert(inked > 50, 'the page canvas has text drawn on it');
}

/** axe-core (WCAG 2.1 A and AA, best practices) on the page or one region: nothing critical or serious, contrast included. */
async function expectAccessible(page, what, selector = 'body') {
  await page.evaluate(axeSource);
  const result = await page.evaluate(
    (target) => window.axe.run(target, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] } }),
    selector,
  );
  const bad = result.violations.filter((violation) => violation.impact === 'critical' || violation.impact === 'serious');
  const lesser = result.violations.filter((violation) => !bad.includes(violation)).map((violation) => violation.id);
  console.log(`      axe on ${what}: ${result.passes.length} rules passed, ${bad.length} critical or serious, ${lesser.length} lesser${lesser.length ? ` (${lesser.join(', ')})` : ''}`);
  assert(bad.length === 0, `${what} has accessibility violations: ${bad.map((violation) => `${violation.id} (${violation.nodes.length}): ${violation.nodes[0]?.html.slice(0, 140)}`).join('; ')}`);
}

/** Every visible button and link has a name; headings never skip a level going down. */
async function expectNamesAndHeadings(page, what) {
  const found = await page.evaluate(() => {
    const visible = (element) => {
      const box = element.getBoundingClientRect();
      return box.width > 0 && box.height > 0 && getComputedStyle(element).visibility !== 'hidden';
    };
    const nameOf = (element) => {
      const labelledby = element.getAttribute('aria-labelledby');
      const byId = labelledby ? labelledby.split(/\s+/).map((id) => document.getElementById(id)?.textContent ?? '').join(' ') : '';
      return (element.getAttribute('aria-label') ?? byId ?? '').trim() || (element.textContent ?? '').trim() || (element.getAttribute('title') ?? '').trim();
    };
    const unnamed = [...document.querySelectorAll('button, a[href], [role="button"], [role="tab"], [role="menuitem"], [role="option"]')]
      .filter(visible)
      .filter((element) => !nameOf(element))
      .map((element) => element.outerHTML.slice(0, 120));
    const levels = [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')].filter(visible).map((heading) => Number(heading.tagName[1]));
    const skips = [];
    for (let i = 1; i < levels.length; i += 1) if (levels[i] > levels[i - 1] + 1) skips.push(`h${levels[i - 1]} → h${levels[i]}`);
    return { unnamed, levels, skips, h1: levels.filter((level) => level === 1).length };
  });
  console.log(`      names and headings on ${what}: ${found.unnamed.length} unnamed controls, headings ${found.levels.join(' ')}`);
  assert(found.unnamed.length === 0, `${what} has controls with no accessible name: ${found.unnamed.join(' | ')}`);
  assert(found.h1 === 1, `${what} has exactly one h1, got ${found.h1}`);
  assert(found.skips.length === 0, `${what} skips heading levels: ${found.skips.join(', ')}`);
}

/** The focused element shows a ring of at least 2 px (its own outline or a focus-within wrapper). */
async function expectFocusVisible(page, what) {
  const ring = await page.evaluate(() => {
    const element = document.activeElement;
    if (!element || element === document.body) return { ok: false, who: 'nothing has focus' };
    const has = (style) => style.outlineStyle !== 'none' && Number.parseFloat(style.outlineWidth) >= 2;
    const shadow = (style) => style.boxShadow && style.boxShadow !== 'none';
    let node = element;
    for (let depth = 0; node && depth < 3; depth += 1, node = node.parentElement) {
      const style = getComputedStyle(node);
      if (has(style) || (node === element && shadow(style))) return { ok: true };
    }
    return { ok: false, who: element.outerHTML.slice(0, 120) };
  });
  assert(ring.ok, `${what} shows no focus ring: ${ring.who}`);
}

/** No sideways scrolling: the document is no wider than the window. */
async function sidewaysOverflow(page) {
  return page.evaluate(() => {
    const doc = document.documentElement;
    if (doc.scrollWidth <= doc.clientWidth + 1) return null;
    // Name the widest element that reaches past the right edge, so a failure says where to look.
    let culprit = '';
    let reach = doc.clientWidth;
    for (const element of document.body.querySelectorAll('*')) {
      const right = element.getBoundingClientRect().right;
      if (right > reach + 1) {
        reach = right;
        culprit = `${element.tagName.toLowerCase()}${element.className && typeof element.className === 'string' ? `.${element.className.split(/\s+/).slice(0, 3).join('.')}` : ''}`;
      }
    }
    return `${doc.scrollWidth}px wide in a ${doc.clientWidth}px window (widest: ${culprit}, to ${Math.round(reach)}px)`;
  });
}

/** Signs in through the API with the page's cookie jar, then boards a proposed terms version as that person. */
async function boardProposedTerms(page, borrowerCode) {
  const api = `${BASE}/api/v1`;
  const borrowers = await (await page.request.get(`${api}/borrowers`)).json();
  const borrower = borrowers.find((row) => row.code === borrowerCode);
  assert(borrower, `the borrower ${borrowerCode} is on file`);
  const detail = await (await page.request.get(`${api}/borrowers/${borrower.id}`)).json();
  const facility = detail.facilities[0];
  const terms = {
    definitions: { ebitda: { base: 'ebitda', addbacks: [] } },
    covenants: [
      {
        id: 'leverage',
        name: 'Total Leverage Ratio',
        archetype: 'leverage',
        params: { debt: 'total_debt', ebitda: 'ebitda' },
        test: { operator: '<=', threshold: '3.50', unit: 'ratio' },
        measurement: { basis: 'ttm', frequency: 'quarterly' },
        rounding: { dp: 2, mode: 'half_up' },
      },
    ],
    reporting_requirements: [],
    borrowing_base: null,
  };
  const made = await page.request.post(`${api}/facilities/${facility.id}/terms`, { data: { terms, effective_from: '2027-01-01' } });
  assert(made.status() === 201, `the terms were boarded as a proposed version, got ${made.status()}: ${await made.text()}`);
  return (await made.json()).approval_item_id;
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
      // The As-of control opens what the simulated clock is.
      await page.locator('[data-as-of]').click();
      await page.getByText('Simulated clock', { exact: true }).first().waitFor();
      await page.locator('[data-freshness]').waitFor();
      await page.keyboard.press('Escape');
    },
  },
  {
    name: 'an analyst works the queue: opens a breach in the workspace drawer, reads its evidence, opens a figure’s source, meets the authority gate and routes it to a credit officer',
    async run(page) {
      await signIn(page, ANALYST);
      const subtitle = (await page.locator('[data-subtitle]').textContent()) ?? '';
      assert(/within your Credit analyst authority/.test(subtitle) && /for Credit officer/.test(subtitle), `the subtitle names the reader’s authority and who decides the rest, got: ${subtitle}`);
      const rows = queueRows(page);
      assert((await rows.count()) > 0, 'the queue has items');
      await page.getByRole('radio', { name: /Critical/ }).click();
      await page.waitForURL(/severity=critical/);
      const breaches = rows.filter({ hasText: BREACH });
      assert((await breaches.count()) > 0, 'a critical covenant breach is in the queue (reseed the dev database if earlier runs decided them all)');
      // Prefer a breach that has not been routed yet, so the routing itself is exercised.
      const unrouted = breaches.filter({ hasNotText: /routed to/ });
      const chosen = (await unrouted.count()) > 0 ? unrouted.first() : breaches.first();
      const borrower = ((await chosen.locator('th').first().textContent()) ?? '').trim();
      // A locator that still finds the row once it has been routed.
      const target = breaches.filter({ has: page.locator('th', { hasText: borrower }) });
      // The routing column says who may decide: a gate tag naming the role.
      await target.getByText('Credit officer sign-off').waitFor();
      await target.click();
      assert((await target.getAttribute('aria-selected')) === 'true', 'the opened row is the selected row');

      const panel = await expectItemInDrawer(page);
      await panel.getByRole('heading', { level: 2 }).waitFor();
      await panel.getByRole('link', { name: borrower }).waitFor();
      await panel.getByText('Evidence', { exact: true }).waitFor();
      await panel.getByText('The calculation', { exact: true }).waitFor();
      // The command centre's own panel below the table is gone: the drawer is the only place the item is shown.
      assert((await page.locator('main [data-work-item]').count()) === 0, 'no item panel is drawn inside the page');

      // A figure in the evidence opens its source beside the page; the calculation's input opens the highlighted page.
      await panel.getByRole('button', { name: 'Open', exact: true }).first().click();
      const source = page.locator('[data-source-drawer]');
      await source.getByRole('heading', { name: 'Total Leverage Ratio' }).waitFor();
      await source.getByRole('button', { name: /Long-term debt, net of current portion/ }).first().click();
      await source.getByRole('heading', { name: 'Long-term debt, net of current portion' }).waitFor();
      const value = (await source.locator('[data-source-value]').textContent()) ?? '';
      await expectHighlightedPage(page, value.replace(/^\$/, '').replace(/,000$/, ''));
      // The source drawer is not modal: the queue behind it still takes a click.
      assert(await rows.first().isEnabled(), 'the queue stays usable while the source is open');
      await source.getByRole('button', { name: 'Close the source' }).click();
      await source.waitFor({ state: 'detached' });

      // The decision: choice cards that the analyst cannot use, and the gate that says who can.
      const form = panel.getByRole('form', { name: 'Record a decision' });
      const choices = form.getByRole('radio');
      assert((await choices.count()) > 0, 'the decision is offered as choice cards');
      assert(await choices.first().isDisabled(), 'the analyst cannot choose a decision on a breach');
      assert(await form.getByRole('button', { name: 'Record decision' }).isDisabled(), '"Record decision" is off for the analyst');
      const gate = form.locator('[data-authority-gate]');
      await gate.getByText('This decision is outside your authority').waitFor();
      await gate.getByText('Credit officer sign-off').waitFor();
      await gate.getByText(/permission to decide the response to a breach|It needs permission to/).waitFor();
      if ((await gate.locator('[data-routed]').count()) === 0) {
        // One holder: the button names the person. Several: a list to choose from, and the button names the role.
        const route = gate.getByRole('button', { name: /^Route to .+ for sign-off$/ });
        await route.click();
        const toast = page.getByText(/^Routed to [A-Z]/).first();
        await toast.waitFor();
        const who = ((await toast.textContent()) ?? '').replace(/^Routed to /, '').trim();
        await gate.locator('[data-routed]').getByText(new RegExp(`Routed to ${who}, `)).waitFor();
        await target.getByText(`routed to ${who}`).waitFor();
        console.log(`      routed ${borrower}’s breach to ${who}`);
      } else {
        console.log(`      ${borrower}’s breach was already routed: ${(await gate.locator('[data-routed]').textContent())?.trim()}`);
      }
      assert((await panel.getAttribute('data-item-status')) === 'open', 'routing leaves the item open for the officer');

      // Ask Copilot about the item: the Copilot tab, off here with the reason, and nothing is sent.
      await panel.locator('[data-ask-copilot]').click();
      const drawer = workspace(page);
      assert((await drawer.getByRole('tab', { name: /Copilot/ }).getAttribute('aria-selected')) === 'true', 'the Copilot tab is selected');
      const copilot = drawer.locator('[data-copilot]');
      await copilot.locator('[data-copilot-empty]').waitFor();
      await copilot.getByText('The Copilot cannot answer here').waitFor();
      await copilot.getByText(/recorded model responses/).waitFor();
      const starters = copilot.locator('[data-starter]');
      assert((await starters.count()) > 0 && (await starters.first().isDisabled()), 'the starter questions are off while no model is connected');
      await drawer.getByRole('tab', { name: /Exception & decision/ }).click();
      await panel.waitFor();
    },
  },
  {
    name: 'with no model connected, "Run … now" on a borrower’s cycle is off and says why; nothing is run',
    async run(page) {
      await signIn(page, ANALYST);
      // A cycle whose next stage is free to run (not waiting for a person) shows the button; find one.
      const borrowers = await (await page.request.get(`${BASE}/api/v1/borrowers`)).json();
      const runs = [];
      page.on('request', (request) => {
        if (request.method() === 'POST' && /\/cycles\/[^/]+\/run/.test(request.url())) runs.push(request.url());
      });
      for (const borrower of borrowers) {
        await page.goto(`${BASE}/borrowers/${borrower.code}/covenants`);
        await page.waitForSelector('[data-ready]');
        const stage = page.locator('[data-run-stage]');
        if ((await stage.count()) === 0) continue;
        await stage.getByText(/Agents cannot run here|is waiting for a person|Nothing to run/).waitFor();
        if ((await stage.getByText(/Agents cannot run here/).count()) === 0) continue;
        const button = stage.getByRole('button', { name: /^Run .+ now$/ });
        assert(await button.isDisabled(), '"Run … now" is off without a model');
        await stage.getByText(/recorded model responses/).waitFor();
        console.log(`      ${borrower.name}: “${(await button.textContent())?.trim()}” is off: ${(await stage.locator('p').first().textContent())?.trim()}`);
        assert(runs.length === 0, 'no stage was asked to run');
        return;
      }
      throw new Error('no borrower has a cycle whose next stage is free to run, so the off state could not be checked (decide a breach first, or reseed)');
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
      await drawer.getByRole('button', { name: /Long-term debt, net of current portion/ }).first().click();
      await drawer.getByRole('heading', { name: 'Long-term debt, net of current portion' }).waitFor();
      const value = (await drawer.locator('[data-source-value]').textContent()) ?? '';
      await expectHighlightedPage(page, value.replace(/^\$/, '').replace(/,000$/, ''));
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
    name: 'a credit officer records a decision on a breach with a reason, sees it leave the queue, finds it in the ledger and verifies the chain',
    async run(page) {
      await signIn(page, OFFICER);
      assert((await page.locator('[data-user-role]').textContent()) === 'Credit officer', 'the shell shows the officer’s role');
      const rows = queueRows(page);
      const before = await rows.count();
      const breaches = rows.filter({ hasText: BREACH });
      assert((await breaches.count()) > 0, 'an open covenant breach is in the queue (reseed the dev database if earlier runs decided them all)');
      const target = breaches.last();
      const borrower = ((await target.locator('th').first().textContent()) ?? '').trim();
      await target.getByText('Within your authority').waitFor();
      await target.click();
      const panel = await expectItemInDrawer(page);
      await panel.getByText(/Covenant breach|reported compliant/i).first().waitFor();
      const itemId = await panel.getAttribute('data-work-item');
      const form = panel.getByRole('form', { name: 'Record a decision' });
      assert((await form.locator('[data-authority-gate]').count()) === 0, 'no authority gate for the officer');
      // A decision that needs a reason is not sent without one.
      await form.getByRole('radio', { name: /Reserve rights/ }).click();
      assert((await form.getByRole('radio', { name: /Reserve rights/ }).getAttribute('aria-checked')) === 'true', 'the card is chosen');
      await form.getByRole('button', { name: 'Record decision' }).click();
      await form.getByText(/This decision needs a reason/).waitFor();
      const reason = `Journey ${new Date().toISOString()}: certificate and calculation disagree; reserve rights pending the borrower's response.`;
      await form.getByLabel(/Reason/).fill(reason);
      await form.getByRole('button', { name: 'Record decision' }).click();
      await page.getByText('Recorded: Reserve rights').first().waitFor();
      await page.waitForFunction(
        (expected) => document.querySelectorAll('section[aria-label="Exception queue"] table tbody tr[data-row]').length === expected,
        before - 1,
      );
      // The drawer now shows the decision on record, not an open form.
      await workspace(page).locator(`[data-work-item="${itemId}"][data-item-status="decided"]`).getByText('Decision on record').waitFor();
      assert((await rows.filter({ hasText: borrower }).filter({ hasText: BREACH }).count()) === 0, 'the breach left the queue');

      await page.goto(`${BASE}/governance?tab=ledger&entity=${itemId}`);
      await page.waitForSelector('[data-ready]');
      const event = page.locator('table tbody tr').filter({ hasText: 'Decision recorded' }).first();
      await event.waitFor();
      const text = (await event.textContent()) ?? '';
      assert(text.includes('Helen Strand'), 'the ledger names who decided');
      assert(text.includes('Reserve rights') && text.includes(reason), 'the ledger carries the decision and its reason');
      await page.getByRole('button', { name: 'Verify the chain' }).click();
      const result = page.locator('[data-chain-result]').getByText(/Chain intact: [\d,]+ events checked/);
      await result.waitFor({ timeout: 60000 });
      console.log(`      ${(await result.textContent())?.trim()}`);
      await signOut(page);
    },
  },
  {
    name: 'four eyes: the person who boarded terms is refused when they approve them; switching demo user to a credit officer, the second person rejects them',
    async run(page) {
      await signIn(page, CREDIT_ADMIN);
      const itemId = await boardProposedTerms(page, BORROWER);
      await page.goto(`${BASE}/command-centre?item=${itemId}`);
      await page.waitForSelector('[data-ready]');
      const panel = await expectItemInDrawer(page, itemId);
      const form = panel.getByRole('form', { name: 'Record a decision' });
      await form.getByText('Needs a second person: whoever prepared this cannot approve it.').waitFor();
      await form.getByRole('radio', { name: /^Approve/ }).click();
      await form.getByLabel(/Reason/).fill('Journey: the person who boarded these terms tries to approve them.');
      await form.getByRole('button', { name: 'Record decision' }).click();
      await form.getByText('Not recorded: a second person is required').waitFor();
      await form.getByText(/The server said: “.*different person/).waitFor();
      assert((await panel.getAttribute('data-item-status')) === 'open', 'the item is still open after the refusal');

      // Switch demo user: a real sign-out and sign-in as the credit officer, never a change of role on one identity.
      await page.getByRole('button', { name: /Account menu/ }).click();
      await page.getByText('Switch demo user').waitFor();
      await page.locator(`[data-demo-user="${OFFICER}"]`).click();
      await page.getByText('Signed in as Helen Strand').first().waitFor();
      await page.locator('[data-user-name]', { hasText: 'Helen Strand' }).waitFor();
      assert((await page.locator('[data-user-role]').textContent()) === 'Credit officer', 'the shell shows the new person’s role');

      await page.goto(`${BASE}/command-centre?item=${itemId}`);
      await page.waitForSelector('[data-ready]');
      const again = await expectItemInDrawer(page, itemId);
      const second = again.getByRole('form', { name: 'Record a decision' });
      await second.getByRole('radio', { name: /^Reject/ }).click();
      await second.getByLabel(/Reason/).fill('Journey: boarded by the four-eyes test; rejected by a second person so nothing is left open.');
      await second.getByRole('button', { name: 'Record decision' }).click();
      await page.getByText('Recorded: Reject').first().waitFor();
      await workspace(page).locator(`[data-work-item="${itemId}"][data-item-status="decided"]`).waitFor();
    },
  },
  {
    name: 'the keyboard works the queue: J and K move, Enter opens the drawer, Esc closes it and gives focus back; Ctrl K filters; [ folds the rail',
    async run(page) {
      await signIn(page, ANALYST);
      const rows = queueRows(page);
      assert((await rows.count()) >= 3, 'the queue has at least three items');
      await rows.first().focus();
      await page.keyboard.press('Shift'); // marks keyboard modality so :focus-visible applies
      await expectFocusVisible(page, 'the first queue row');
      const focusedIndex = () => page.evaluate(() => document.activeElement?.getAttribute('data-index'));
      await page.keyboard.press('j');
      assert((await focusedIndex()) === '1', 'J moves to the next row');
      await page.keyboard.press('j');
      assert((await focusedIndex()) === '2', 'J again moves on');
      await page.keyboard.press('k');
      assert((await focusedIndex()) === '1', 'K moves back');
      await page.keyboard.press('ArrowDown');
      assert((await focusedIndex()) === '2', 'the down arrow moves too');
      await page.keyboard.press('Enter');
      const panel = await expectItemInDrawer(page);
      assert((await rows.nth(2).getAttribute('aria-selected')) === 'true', 'Enter opens the focused row');
      await page.waitForURL(/[?&]item=/).catch(() => {}); // the link to the item, when the screen writes it
      // Focus stays on the queue, so J moves on and the drawer follows.
      const firstId = await panel.getAttribute('data-work-item');
      await page.keyboard.press('k');
      await page.keyboard.press('Enter');
      await page.waitForFunction((id) => document.querySelector('[data-drawer] [data-work-item]')?.getAttribute('data-work-item') !== id, firstId);
      assert((await rows.nth(1).getAttribute('aria-selected')) === 'true', 'the drawer follows the row opened next');
      await page.keyboard.press('Escape');
      await workspace(page).waitFor({ state: 'detached' });
      assert((await focusedIndex()) === '1', 'Esc closes the drawer and focus is on the row it came from');
      await expectFocusVisible(page, 'the row after Esc');

      // Esc from inside the drawer also gives focus back to the queue.
      await page.keyboard.press('Enter');
      await expectItemInDrawer(page);
      await workspace(page).getByRole('tab', { name: /Exception & decision/ }).focus();
      await page.keyboard.press('Escape');
      await workspace(page).waitFor({ state: 'detached' });
      const back = await page.evaluate(() => document.activeElement?.closest('tr[data-row]')?.getAttribute('data-index') ?? document.activeElement?.tagName);
      assert(back === '1', `Esc from inside the drawer returns focus to the row that opened it, got ${back}`);

      // Ctrl K: the command palette filters the queue.
      await page.keyboard.press('Control+k');
      const search = page.getByRole('combobox', { name: 'Search' });
      await search.waitFor();
      await search.fill('critical');
      await page.getByRole('option', { name: /Show critical exceptions/ }).waitFor();
      await page.keyboard.press('Enter');
      await page.waitForURL(/severity=critical/);
      const critical = await rows.count();
      assert(critical > 0, 'the palette left critical items in view');
      for (let i = 0; i < critical; i += 1) await rows.nth(i).getByText('Critical', { exact: true }).waitFor();

      // [ folds and unfolds the rail; the choice is the person's.
      await page.locator('main').click({ position: { x: 5, y: 5 } });
      const rail = page.locator('[data-rail]');
      const was = await rail.getAttribute('data-rail');
      await page.keyboard.press('[');
      await page.waitForFunction((previous) => document.querySelector('[data-rail]')?.getAttribute('data-rail') !== previous, was);
      await page.keyboard.press('[');
      await page.waitForFunction((previous) => document.querySelector('[data-rail]')?.getAttribute('data-rail') === previous, was);
    },
  },
  {
    name: 'no page scrolls sideways at 360, 390, 820, 1024, 1280 or 1440 px, on every main route and with the drawer open',
    async run(page) {
      await signIn(page, ANALYST);
      const routes = [
        '/command-centre',
        '/portfolio',
        '/borrowers',
        `/borrowers/${BORROWER}`,
        `/borrowers/${BORROWER}/covenants`,
        `/borrowers/${BORROWER}/spreads`,
        '/calendar',
        '/review-room',
        '/agent-activity',
        '/governance',
        '/governance?tab=ledger',
      ];
      const problems = [];
      for (const width of WIDTHS) {
        await page.setViewportSize({ width, height: 900 });
        for (const route of routes) {
          await page.goto(`${BASE}${route}`);
          await page.waitForSelector('[data-ready]');
          await page.waitForTimeout(150);
          const over = await sidewaysOverflow(page);
          if (over) problems.push(`${route} at ${width}: ${over}`);
        }
        // The command centre with an item open in the drawer, and with the Copilot tab.
        await page.goto(`${BASE}/command-centre`);
        await page.waitForSelector('[data-ready]');
        await queueRows(page).first().click();
        await expectItemInDrawer(page);
        await page.waitForTimeout(150);
        let over = await sidewaysOverflow(page);
        if (over) problems.push(`/command-centre with the drawer open at ${width}: ${over}`);
        await workspace(page).getByRole('tab', { name: /Copilot/ }).click();
        await workspace(page).locator('[data-copilot-empty]').waitFor();
        over = await sidewaysOverflow(page);
        if (over) problems.push(`/command-centre with the Copilot open at ${width}: ${over}`);
        // A figure's source beside the page.
        await page.goto(`${BASE}/borrowers/${BORROWER}/covenants`);
        await page.waitForSelector('[data-ready]');
        await page.locator('table tbody tr[data-row]').filter({ hasText: 'Total Leverage Ratio' }).first().getByRole('button', { name: /Calculated by code/ }).first().click();
        await page.locator('[data-source-drawer]').getByRole('heading', { name: 'Total Leverage Ratio' }).waitFor();
        over = await sidewaysOverflow(page);
        if (over) problems.push(`covenants with the source open at ${width}: ${over}`);
      }
      console.log(`      checked ${WIDTHS.length} widths × ${routes.length + 3} views`);
      assert(problems.length === 0, `pages scroll sideways:\n${problems.join('\n')}`);
    },
  },
  {
    name: 'accessibility: axe finds nothing critical or serious; every control is named; headings in order; the drawer and the source pass too',
    async run(page) {
      await page.goto(`${BASE}/sign-in`);
      await page.getByLabel('Email').waitFor();
      await expectAccessible(page, 'sign-in');
      await expectNamesAndHeadings(page, 'sign-in');
      await signIn(page, ANALYST);
      await expectAccessible(page, 'the command centre');
      await expectNamesAndHeadings(page, 'the command centre');
      const target = queueRows(page).filter({ hasText: BREACH }).first();
      await ((await target.count()) > 0 ? target : queueRows(page).first()).click();
      await expectItemInDrawer(page);
      await page.waitForTimeout(250);
      await expectAccessible(page, 'the command centre with an exception in the drawer');
      await expectNamesAndHeadings(page, 'the command centre with an exception in the drawer');
      await workspace(page).getByRole('tab', { name: /Copilot/ }).click();
      await workspace(page).locator('[data-copilot-empty]').waitFor();
      await expectAccessible(page, 'the Copilot tab', '[data-drawer]');
      await page.keyboard.press('Escape');
      await workspace(page).waitFor({ state: 'detached' });
      for (const [route, what] of [
        ['/portfolio', 'the portfolio'],
        [`/borrowers/${BORROWER}/covenants`, 'a borrower’s covenants'],
        ['/governance?tab=ledger', 'the ledger'],
        ['/agent-activity', 'agent activity'],
      ]) {
        await page.goto(`${BASE}${route}`);
        await page.waitForSelector('[data-ready]');
        await expectAccessible(page, what);
        await expectNamesAndHeadings(page, what);
      }
      await page.goto(`${BASE}/borrowers/${BORROWER}/covenants`);
      await page.waitForSelector('[data-ready]');
      await page.locator('table tbody tr[data-row]').filter({ hasText: 'Total Leverage Ratio' }).first().getByRole('button', { name: /Calculated by code/ }).first().click();
      await page.locator('[data-source-drawer]').getByRole('heading', { name: 'Total Leverage Ratio' }).waitFor();
      await expectAccessible(page, 'the source drawer', '[data-source-drawer]');
      // The source drawer's controls show focus from the keyboard.
      await page.locator('[data-source-drawer]').getByRole('button', { name: 'Close the source' }).focus();
      await page.keyboard.press('Shift');
      await expectFocusVisible(page, 'the source drawer’s close button');
    },
  },
];

const onlyIndex = process.argv.indexOf('--only');
const only = onlyIndex > -1 ? (process.argv[onlyIndex + 1] ?? '').split(',').map(Number) : null;
const chosen = journeys.filter((_, index) => !only || only.includes(index + 1));

const browser = await chromium.launch({ headless: !process.env.HEADED });
let failed = 0;
for (const journey of chosen) {
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
    console.log(`FAIL  ${journey.name}\n      ${String(error.message ?? error).split('\n').slice(0, 12).join('\n      ')}\n      screenshot: ${shot}`);
  } finally {
    await context.close();
  }
}
await browser.close();
console.log(failed === 0 ? `PASSED: ${chosen.length} ${chosen.length === 1 ? 'journey' : 'journeys'}` : `FAILED: ${failed} of ${chosen.length} journeys`);
process.exit(failed === 0 ? 0 : 1);
