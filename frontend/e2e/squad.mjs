// frontend/e2e/squad.mjs
// Journeys for the Squad experience (docs/specs/2026-11-20-squad-experience-design.md section 14).
// Usage: pnpm e2e:squad     (BASE_URL=http://localhost:5173; HEADED=1 to watch)
// Run `uv run python -m app.squad_demo` once on a freshly seeded book first.
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
const MANAGER = 'dana.whitfield@bankofstoic.example';
const LOOKS = ['Night', 'Warm paper', 'Cool slate', 'Lavender mist', 'Sage'];
const WIDTHS = [1000, 1100, 1280, 1440, 1600, 1920];
const failuresDir = resolve(dirname(fileURLToPath(import.meta.url)), 'failures');

const assert = (ok, message) => {
  if (!ok) throw new Error(message);
};

async function signIn(page, email) {
  await page.goto(`${BASE}/sign-in`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(`${BASE}/`);
}

const api = (page, path, init) => page.request.fetch(`${BASE}/api/v1${path}`, init).then((r) => r.json());

/** What the record says needs this person, read through the same API the page reads. */
async function record(page) {
  const b = await api(page, '/me/briefing');
  return { b, needs: b.items.filter((i) => i.needs_you), clients: b.open_clients };
}

/** The route form lists everyone who may decide the case; the journey sends it to Helen Strand. */
async function chooseOfficer(card) {
  assert((await card.getByLabel('Send to').inputValue()) === '', 'the route form preselected a person');
  assert(await card.getByRole('button', { name: 'Choose who decides' }).isDisabled(), 'Send was enabled before a person was chosen');
  const value = await card.locator('select option', { hasText: 'Helen Strand' }).first().getAttribute('value');
  await card.getByLabel('Send to').selectOption(value);
}

const journeys = [];
const journey = (name, fn) => journeys.push({ name, fn });

journey('home: the count equals the items listed, and each item opens its own client at its case', async ({ page }) => {
  await signIn(page, ANALYST);
  const { b, needs } = await record(page);
  const sentence = needs.length ? (needs.length === 1 ? '1 needs you' : `${needs.length} need you`) : 'Nothing needs you.';
  await page.getByText(sentence, { exact: true }).waitFor();
  assert((await page.getByRole('list', { name: 'Needs you' }).getByRole('listitem').count()) === needs.length, 'listed items differ from the count');
  assert(needs.length > 0, 'the seeded book should leave the analyst something to do (run app.squad_demo)');
  for (const item of needs) {
    await page.goto(`${BASE}/`);
    await page.getByRole('link', { name: new RegExp(`${item.borrower_name} · ${item.title}`.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).first().click();
    await page.waitForURL(new RegExp(`/clients/${item.borrower_code}`));
    await page.getByRole('heading', { level: 1, name: item.borrower_name }).waitFor();
    if (item.work_item_id) {
      const card = page.locator(`[data-work-item="${item.work_item_id}"][data-focused="true"]`);
      await card.waitFor();
      // no other client's name appears as a message heading on this thread
      const others = b.items.filter((i) => i.borrower_code !== item.borrower_code).map((i) => i.borrower_name);
      const text = await page.locator('.sq-messages').innerText();
      for (const name of others) assert(!text.includes(name), `another client's case (${name}) is on ${item.borrower_name}'s thread`);
    }
  }
});

journey('nav: "Open cases" lists exactly the clients with something open, and each lands in its thread', async ({ page }) => {
  await signIn(page, ANALYST);
  const { clients } = await record(page);
  await page.getByRole('button', { name: /expand navigation/i }).click();
  const links = page.getByRole('navigation', { name: 'Open cases' }).getByRole('link');
  assert((await links.count()) === clients.length, 'Open cases differs from the clients with open work');
  const portfolio = (await api(page, '/me/portfolio')).sections.flatMap((x) => x.rows);
  for (const c of clients) assert(portfolio.find((r) => r.code === c.code)?.open === c.open, `${c.name}: the nav count differs from the Portfolio's Open`);
  assert(portfolio.filter((r) => r.open > 0).length === clients.length, 'a client with open cases is missing from Open cases, or one without is listed');
  for (const c of clients) {
    await page.getByRole('navigation', { name: 'Open cases' }).getByRole('link', { name: new RegExp(c.name) }).click();
    await page.waitForURL(new RegExp(`/clients/${c.code}$`));
    await page.getByRole('heading', { level: 1, name: c.name }).waitFor();
  }
});

journey('palette: Ctrl K reaches any client by name, from any screen', async ({ page }) => {
  await signIn(page, ANALYST);
  const [first] = (await api(page, '/borrowers')).slice(0, 1);
  await page.keyboard.press('Control+K');
  await page.getByRole('combobox').fill(first.name.split(',')[0].slice(0, 8));
  await page.getByRole('option', { name: new RegExp(first.name.slice(0, 8)) }).first().click();
  await page.waitForURL(new RegExp(`/clients/${first.code}$`));
});

journey('portfolio: every client appears once, by measure, and each row opens its own thread', async ({ page }) => {
  await signIn(page, ANALYST);
  await page.getByRole('link', { name: /my portfolio/i }).click();
  await page.waitForURL(`${BASE}/portfolio`);
  const data = await api(page, '/me/portfolio');
  const all = data.sections.flatMap((s) => s.rows);
  const borrowers = await api(page, '/borrowers');
  assert(all.length === borrowers.length && new Set(all.map((r) => r.code)).size === all.length, 'a client is missing or listed twice');
  for (const r of all.slice(0, 3)) {
    await page.goto(`${BASE}/portfolio`);
    await page.getByRole('link', { name: r.name, exact: true }).click();
    await page.waitForURL(new RegExp(`/clients/${r.code}$`));
    await page.getByRole('heading', { level: 1, name: r.name }).waitFor();
  }
});

journey('portfolio: every client row shows what its client file shows as the latest point', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(e.message));
  await signIn(page, ANALYST);
  const data = await api(page, '/me/portfolio');
  const all = data.sections.flatMap((s) => s.rows);
  await page.goto(`${BASE}/portfolio`);
  await page.locator('[data-ready]').waitFor();
  const shown = {};
  for (const r of all) shown[r.code] = (await page.locator(`tr[data-borrower="${r.code}"] [data-measure-cell]`).innerText()).trim();
  let mismatches = 0;
  for (const r of all) {
    const file = await api(page, `/borrowers/${r.borrower_id}/measure`);
    if (JSON.stringify(file.points.at(-1)) !== JSON.stringify(r.measure.points.at(-1))) mismatches += 1;
    await page.goto(`${BASE}/clients/${r.code}/file`);
    await page.locator('[data-measure-now]').waitFor();
    const there = (await page.locator('[data-measure-now]').innerText()).trim();
    if (there !== shown[r.code]) mismatches += 1;
    assert((await page.getByRole('alert').count()) === 0, `${r.code}: the client file shows an error`);
  }
  console.log(`      checked ${all.length} clients, ${mismatches} mismatches, ${pageErrors.length} page errors`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(' | ')}`);
  assert(mismatches === 0, `${mismatches} portfolio rows differ from their client file`);
});

journey('deep link: an unknown case id shows the thread, not an error', async ({ page }) => {
  await signIn(page, ANALYST);
  const [first] = await api(page, '/borrowers');
  await page.goto(`${BASE}/clients/${first.code}?case=00000000-0000-0000-0000-000000000000`);
  await page.getByRole('heading', { level: 1, name: first.name }).waitFor();
  assert((await page.getByRole('alert').count()) === 0, 'unknown case id raised an alert');
  assert((await page.locator('[data-focused]').count()) === 0, 'an unknown case id focused something');
});

journey('deep link: an unknown client says so and offers the way home', async ({ page }) => {
  await signIn(page, ANALYST);
  await page.goto(`${BASE}/clients/NOPE`);
  await page.getByRole('alert').getByText(/no client with that code/i).waitFor();
  await page.getByRole('link', { name: /back to squad/i }).click();
  await page.waitForURL(`${BASE}/`);
});

journey('Squad asks: answering with Remember writes the choice with her name, one lesson, and the badge falls', async ({ page }) => {
  await signIn(page, ANALYST);
  const asks = (await api(page, '/work-items?item_type=question')).filter((i) => i.status === 'open');
  if (asks.length === 0) return console.log('  (no open question: already answered on an earlier run; skipping)');
  const ask = asks[0];
  const before = (await record(page)).needs.length;
  await page.goto(`${BASE}/clients/${(await api(page, `/borrowers/${ask.borrower_id}`)).code}?case=${ask.id}`);
  const card = page.locator(`[data-work-item="${ask.id}"]`);
  await card.getByRole('radio').first().check();
  await card.getByRole('checkbox', { name: /remember/i }).check();
  await card.getByLabel(/why\?/i).fill('Mapped the same way on the last two closes.');
  await card.getByRole('button', { name: /confirm/i }).click();
  await page.getByRole('status').filter({ hasText: /Recorded as Priya · remembered/ }).waitFor();
  const decided = await api(page, `/work-items/${ask.id}`);
  assert(decided.status === 'decided' && decided.decided_by, 'the answer was not recorded with a person');
  const lessons = await api(page, '/ledger?action=lesson.recorded&limit=50');
  assert(lessons.some((e) => e.payload.work_item_id === ask.id), 'Remember wrote no lesson');
  await page.waitForFunction(() => !document.body.innerText.includes('How should I map this line?') || !document.querySelector('input[type=radio]'));
  assert((await record(page)).needs.length === before - 1, 'the needs-you count did not fall by one');
});

journey('drafts: edit then Send as Priya records the send and claims no delivery', async ({ page }) => {
  await signIn(page, ANALYST);
  const [row] = (await api(page, '/ledger?action=draft.created&limit=20')).filter((e) => e.payload.kind === 'demo_reminder');
  if (!row) return console.log('  (no demo draft; run app.squad_demo)');
  const draftId = row.entity_id;
  const folded = await api(page, `/threads/${row.payload.borrower_id}`);
  const draft = folded.messages.find((m) => m.type === 'draft' && m.draft_id === draftId);
  if (draft.status === 'sent') return console.log('  (draft already sent on an earlier run; skipping)');
  await page.goto(`${BASE}/clients/${folded.borrower.code}`);
  await page.getByLabel(/^Message to /).fill('Hi, October MRR please. Thanks.');
  await page.getByRole('button', { name: 'Send as Priya' }).click();
  await page.getByRole('status').filter({ hasText: /Send recorded as Priya · not emailed/ }).waitFor();
  const sent = (await api(page, `/ledger?entity_id=${draftId}&limit=10`)).find((e) => e.action === 'draft.sent');
  assert(sent && sent.payload.delivery === 'recorded_only' && sent.actor_type === 'user', 'draft.sent was not recorded as a person, recording only');
  assert((await page.getByRole('button', { name: /send as/i }).count()) === 0, 'a sent draft can be sent again');
});

journey('direct URL: ?case= lands on the same focused card the home item does, for every open case', async ({ page }) => {
  await signIn(page, ANALYST);
  const { needs } = await record(page);
  for (const item of needs.filter((i) => i.work_item_id)) {
    await page.goto(`${BASE}/clients/${item.borrower_code}?case=${item.work_item_id}`);
    await page.getByRole('heading', { level: 1, name: item.borrower_name }).waitFor();
    await page.locator(`[data-work-item="${item.work_item_id}"][data-focused="true"]`).waitFor();
    assert((await page.locator('[data-focused="true"]').count()) === 1, 'more than one card is focused');
  }
});

journey('evidence: a document opens beside the thread and pushes it aside, at every width', async ({ browser }) => {
  for (const width of WIDTHS) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    await signIn(page, ANALYST);
    let withDoc = null;
    let docs = [];
    for (const b of await api(page, '/borrowers')) {
      docs = await api(page, `/borrowers/${b.id}/documents`);
      if (docs.length) { withDoc = b; break; }
    }
    assert(withDoc, 'no client with a document to open as evidence');
    await page.goto(`${BASE}/clients/${withDoc.code}`);
    const before = (await page.locator('.sq-main').boundingBox()).width;
    await page.getByRole('button', { name: new RegExp(`^Open ${docs[0].title}`) }).first().click();
    await page.locator('[data-source-drawer]').waitFor();
    const after = (await page.locator('.sq-main').boundingBox()).width;
    assert(after <= before, `the drawer did not push the thread aside at ${width}px`);
    assert(after >= 480, `the conversation is ${Math.round(after)}px with the drawer open at ${width}px (minimum 480)`);
    assert((await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)), `horizontal page scroll at ${width}px`);
    await context.close();
  }
});

journey('looks: every look keeps text readable and the officer starts in Warm paper', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  await signIn(page, OFFICER);
  assert((await page.evaluate(() => document.querySelector('.sq-root').dataset.look)) === 'warm', 'the officer did not start in Warm paper');
  await context.close();
  const analyst = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await analyst.newPage();
  await signIn(p, ANALYST);
  assert((await p.evaluate(() => document.querySelector('.sq-root').dataset.look)) === 'night', 'the analyst did not start in Night');
  for (const look of LOOKS) {
    await p.getByRole('button', { name: /^look:/i }).click();
    await p.getByRole('menuitemradio', { name: look }).click();
    await p.addScriptTag({ content: axeSource });
    const result = await p.evaluate(() => window.axe.run(document.body, { runOnly: ['color-contrast', 'label', 'button-name', 'link-name'] }));
    const bad = result.violations.map((v) => `${v.id}: ${v.nodes.length}`);
    assert(bad.length === 0, `${look}: accessibility violations: ${bad.join(', ')}`);
  }
  await analyst.close();
});

journey('My Portfolio in Night is a Squad screen: not full width, presence line shown, contrast checks pass', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1920, height: 900 } });
  const page = await context.newPage();
  await signIn(page, ANALYST);
  assert((await page.evaluate(() => document.querySelector('.sq-root').dataset.look)) === 'night', 'the analyst did not start in Night');
  await page.goto(`${BASE}/portfolio`);
  await page.locator('.sq-main[data-surface="squad"]').waitFor();
  await page.getByRole('heading', { level: 1, name: 'My Portfolio' }).waitFor();
  const width = (await page.locator('.sq-main').boundingBox()).width;
  assert(width <= 1280, `the portfolio is ${Math.round(width)}px wide in the shell (expected at most 1280)`);
  assert((await page.locator('.sq-presence').count()) === 1, 'the presence line is missing on My Portfolio');
  await page.addScriptTag({ content: axeSource });
  const result = await page.evaluate(() => window.axe.run(document.body, { runOnly: ['color-contrast', 'label', 'button-name', 'link-name'] }));
  const bad = result.violations.map((v) => `${v.id}: ${v.nodes.length}`);
  assert(bad.length === 0, `Night /portfolio: accessibility violations: ${bad.join(', ')}`);
  assert((await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)), 'horizontal page scroll on /portfolio');
  await context.close();
});

journey('motion: with reduced motion the mark does not move', async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await context.newPage();
  await signIn(page, ANALYST);
  const names = await page.evaluate(() => [...document.querySelectorAll('.sq-mk *')].map((el) => getComputedStyle(el).animationName));
  assert(names.every((n) => n === 'none'), `animation still running under reduced motion: ${names.join(',')}`);
  await context.close();
});

journey('the officer sees only what she can act on, and the count agrees', async ({ page }) => {
  await signIn(page, OFFICER);
  const { needs } = await record(page);
  const sentence = needs.length ? (needs.length === 1 ? '1 needs you' : `${needs.length} need you`) : 'Nothing needs you.';
  await page.getByText(sentence, { exact: true }).waitFor();
});

journey('hand-off: the analyst routes a breach with her view, the officer returns it, it comes back, and the officer decides', async ({ browser }) => {
  const analystCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const a = await analystCtx.newPage();
  await signIn(a, ANALYST);
  const breaches = await api(a, '/work-items?item_type=covenant.breach');
  const open = breaches.find((w) => !w.assigned_to);
  assert(open, 'the seeded book should hold an open, unassigned covenant breach');
  const borrower = await api(a, `/borrowers/${open.borrower_id}`);
  await a.goto(`${BASE}/clients/${borrower.code}?case=${open.id}`);
  const card = a.locator(`[data-work-item="${open.id}"][data-focused="true"]`);
  await chooseOfficer(card); // more than one person may decide a breach
  await card.getByLabel(/your view/i).fill('Cash under the floor two months running; recommend reserving rights.');
  await card.getByRole('button', { name: /^Send to / }).click();
  await a.getByText(/with your view · recorded/).waitFor();
  assert((await card.getByRole('button', { name: 'Record decision' }).count()) === 0, 'the analyst was offered a decision she routed');

  const officerCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const o = await officerCtx.newPage();
  await signIn(o, OFFICER);
  await o.goto(`${BASE}/approvals?case=${open.id}`);
  await o.getByText('Cash under the floor two months running; recommend reserving rights.').first().waitFor();
  await o.getByLabel(/what is missing/i).fill('Attach the signed term sheet for the new round.');
  // Task 5c: the officer says what is needed. One need the seeded book holds exactly once (Squad attaches it), one it does not (Squad drafts the request).
  const docs = await api(o, `/borrowers/${open.borrower_id}/documents`);
  const once = docs.find((d) => d.doc_type && d.period_end && d.status !== 'rejected' && d.doc_type_source === 'system'
    && docs.filter((e) => e.doc_type === d.doc_type && e.period_end === d.period_end && e.status !== 'rejected').length === 1);
  assert(once, 'the seeded client should hold a document that is the only one of its type and month');
  const words = (await api(o, '/words/document-types')).types;
  const monthName = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
  const needs = [{ doc_type: once.doc_type, period_end: once.period_end }, { doc_type: 'tax_return', period_end: '2019-12-31' }];
  for (const [i, n] of needs.entries()) {
    await o.getByRole('button', { name: 'Add something that is needed' }).click();
    await o.getByLabel(`Document type ${i + 1}`).selectOption(n.doc_type);
    await o.getByLabel(`Month ${i + 1}`).fill(n.period_end.slice(0, 7));
  }
  await o.getByRole('button', { name: 'Return to Priya Raman' }).click();
  await o.getByText(/Returned to Priya Raman · recorded/).waitFor();

  await a.goto(`${BASE}/`);
  const back = (await record(a)).needs.find((i) => i.work_item_id === open.id);
  assert(back && back.state === 'returned to you', 'the returned case does not need the analyst');
  await a.goto(`${BASE}/clients/${borrower.code}?case=${open.id}`);
  await a.getByText('Attach the signed term sheet for the new round.').first().waitFor();
  const squadSaid = `Attached the ${words[once.doc_type]} for ${monthName(once.period_end)} that Helen Strand asked for.`;
  await a.getByText(squadSaid).first().waitFor();
  const asked = `Could you send the ${words.tax_return} for ${monthName('2019-12-31')} when you have a moment?`;
  await a.getByText(asked).first().waitFor(); // the draft request to the client is in the thread
  const states = (await api(a, `/cases/${open.id}`)).needs.map((n) => n.state_words);
  assert(states[0].startsWith('Attached: ') && states[1] === 'Asked the client', `the needs read ${JSON.stringify(states)}`);
  await card.getByText(/on file you can attach$/).click(); // the seeded client has documents on file: none here is a defect
  await card.getByRole('button', { name: /^Attach / }).first().click();
  await a.getByText(/attached · recorded$/).waitFor();
  await chooseOfficer(card);
  await card.getByLabel(/your view/i).fill('Term sheet attached; my view stands.');
  await card.getByRole('button', { name: /^Send to / }).click();

  await o.goto(`${BASE}/approvals?case=${open.id}`);
  await o.getByRole('radio', { name: /^Reserve rights/ }).check();
  await o.getByLabel(/^Reason/).fill('Reserving rights until the round closes.');
  await o.getByRole('button', { name: 'Record decision' }).click();
  await o.getByText(/· recorded$/).waitFor();
  const done = await api(o, `/cases/${open.id}`);
  assert(done.status === 'decided' && done.decided_by === 'Helen Strand', 'the officer’s decision was not recorded');
  await analystCtx.close();
  await officerCtx.close();
});

journey('review room: a portfolio manager opens a meeting, moves it to during and raises an action; an analyst is offered no approval or release', async ({ browser }) => {
  const pm = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await pm.newPage();
  await signIn(p, MANAGER);
  await p.goto(`${BASE}/review-room`);
  await p.locator('.sq-main[data-surface="squad"]').waitFor();
  const title = `Portfolio review ${new Date().toISOString().slice(11, 19)}`;
  // the meeting form only: the actions form on the same page has fields of its own
  const form = p.locator('form').filter({ has: p.getByRole('button', { name: 'Create the meeting' }) });
  await form.getByLabel('Title').fill(title);
  await form.getByLabel('Meeting date').fill('2026-11-30');
  await form.getByRole('button', { name: 'Create the meeting' }).click();
  await p.getByText(/Meeting created · .* recorded/).waitFor();
  const meetings = await api(p, '/review-meetings');
  const meeting = meetings.find((m) => m.title === title);
  assert(meeting, 'the meeting was not recorded');
  await p.goto(`${BASE}/review-room?meeting=${meeting.id}`);
  await p.getByRole('button', { name: 'Move to during' }).click();
  await p.getByText(/Meeting moved to: during · recorded/).waitFor();
  assert((await api(p, '/review-meetings')).find((m) => m.id === meeting.id).phase === 'during', 'the phase was not recorded');
  // Raise an action: Client, Action, Owner and Due are the form's fields (read from `Actions` in the review room).
  const actionTitle = `Follow up ${title}`;
  const actionForm = p.locator('form').filter({ has: p.getByRole('button', { name: 'Raise the action' }) });
  await actionForm.getByRole('combobox', { name: 'Client' }).click();
  await p.getByRole('option').nth(1).click(); // option 0 is "Choose a client"
  await actionForm.getByLabel('Action').fill(actionTitle);
  await actionForm.getByLabel('Due').fill('2026-12-15');
  await actionForm.getByRole('button', { name: 'Raise the action' }).click();
  await p.getByText(/Action raised · recorded/).waitFor();
  assert((await api(p, '/actions?status=all')).some((a) => a.title === actionTitle), 'the action was not recorded');
  await pm.close();
  const an = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const a = await an.newPage();
  await signIn(a, ANALYST);
  await a.goto(`${BASE}/review-room?meeting=${meeting.id}`);
  await a.getByRole('heading', { name: title }).waitFor();
  // The server grants an analyst `manage_actions`, so she may move a phase; what she is never offered is an approval or a release.
  const sheets = await api(a, '/review-sheets');
  for (const sheet of sheets.slice(0, 5)) {
    await a.goto(`${BASE}/review-room?sheet=${sheet.id}`);
    await a.locator('[data-review-sheet]').waitFor();
    assert((await a.locator('[data-review-sheet]').getByRole('radio', { name: /^Approve/ }).count()) === 0, 'an analyst was offered the commentary approval');
    assert((await a.locator('[data-review-sheet]').getByRole('button', { name: 'Record decision' }).count()) === 0, 'an analyst was offered to record the approval');
  }
  const code = (await api(a, '/borrowers'))[0].code; // a seeded book may hold no review sheet yet: the loop above then has nothing to check
  await a.goto(`${BASE}/clients/${code}/file/packages`);
  await a.getByRole('heading', { name: 'Schedules' }).waitFor();
  assert((await a.getByRole('button', { name: 'Run schedules that are due' }).count()) === 0, 'an analyst was offered the schedule run');
  await an.close();
});

journey('old addresses: every retired cockpit address lands on a Squad place that shows the person something, never a refusal', async ({ browser }) => {
  const ADMIN = 'admin@bankofstoic.example';
  for (const [who, email] of [['analyst', ANALYST], ['officer', OFFICER], ['administrator', ADMIN]]) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    await signIn(page, email);
    const oversight = (await api(page, '/me/briefing')).oversight?.offered === true;
    const [first] = await api(page, '/borrowers');
    const docs = await api(page, `/borrowers/${first.id}/documents`);
    const cases = [
      [`/borrowers/${first.code}/covenants`, `/clients/${first.code}/file/covenants`],
      [`/borrowers/${first.code}/packages`, `/clients/${first.code}/file/packages`],
      [`/borrowers/${first.code}`, `/clients/${first.code}/file`],
      ['/borrowers', '/portfolio'],
      ['/command-centre', '/'],
      ['/calendar', '/'],
      ['/design', '/'],
      ['/governance', oversight ? '/oversight/governance' : '/'],
      ['/governance?tab=ledger', oversight ? '/oversight/ledger' : '/'],
      ['/agent-activity?run=abc', oversight ? '/oversight/activity' : '/'],
    ];
    if (docs.length) cases.push([`/borrowers/${first.code}/documents/${docs[0].id}?page=1`, `/clients/${first.code}/file/documents`]);
    for (const [from, to] of cases) {
      await page.goto(`${BASE}${from}`);
      await page.waitForURL((url) => url.pathname === to, { timeout: 10000 });
      // The page is ready when its own content has loaded: only then can a refusal be ruled out.
      await page.waitForLoadState('networkidle');
      await page.locator('[data-ready], .sq-main h1').first().waitFor({ timeout: 15000 });
      const refusals = await page.getByRole('alert').allTextContents();
      assert(refusals.length === 0, `${who}: ${from} landed on an alert: ${refusals.join(' | ')}`);
    }
    // A path nothing answers says so and offers the way home.
    await page.goto(`${BASE}/borrowers/${first.code}/spreads/deeper/still`);
    await page.getByText('There is no such page.').waitFor();
    await page.getByRole('link', { name: 'Back to Squad' }).waitFor();
    await context.close();
  }
});

journey('held reading: Stripple’s held spreadsheet question opens focused in its client thread with its case showing', async ({ page }) => {
  await signIn(page, ANALYST);
  const held = [...(await api(page, '/work-items?item_type=spread.value_unverified')), ...(await api(page, '/work-items?item_type=spread.does_not_foot'))];
  assert(held.length > 0, 'the seeded innovation book should hold one spread for a person (Stripple)');
  const borrower = await api(page, `/borrowers/${held[0].borrower_id}`);
  await page.goto(`${BASE}/clients/${borrower.code}?case=${held[0].id}`);
  const card = page.locator(`[data-work-item="${held[0].id}"][data-focused="true"]`);
  await card.locator('[data-case]').waitFor();
  assert((await card.locator('[data-case]').getAttribute('data-item-status')) === 'open', 'the held case is open');
  // Held figures with their repair actions need a spread that holds figures: frontend/e2e/repair.mjs journey 1 covers them.
});

const VIEWS = ['', '/spreads', '/covenants', '/documents', '/funding', '/loans', '/reviews', '/packages', '/runs', '/history'];

async function noScroll(page, where) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `horizontal page scroll on ${where}`);
}

/** For a measure whose latest point the API says is unmeasured, the cell must show the API's note (or "Not measured"),
 * no digit, and the bars must draw that point as an outline. Compared with the API, never with the page itself. */
async function checkUnmeasured(cell, bars, series, where) {
  const last = series.points.at(-1);
  if (!last || last.fact) return;
  const text = (await cell.innerText()).trim();
  assert(text === (last.note ?? 'Not measured'), `${where}: shows "${text}" for an unmeasured point (the API says "${last.note}")`);
  assert(!/\d/.test(text), `${where}: a digit is shown for an unmeasured point`);
  const kinds = await bars.locator('.sq-bar').evaluateAll((els) => els.map((b) => b.getAttribute('data-point')));
  assert(kinds.at(-1) === 'none', `${where}: the unmeasured point is drawn as ${kinds.at(-1)}, not as an outline`);
}

journey('self-check: the unmeasured check fails on a page that shows a zero for an unmeasured point', async ({ page }) => {
  await page.setContent('<table><tr><td id="cell">0</td><td id="bars"><span class="sq-bar" data-point="low"></span></td></tr></table>');
  const series = { points: [{ period_end: '2026-10-31', fact: null, note: 'Not measured' }] };
  let caught = false;
  try {
    await checkUnmeasured(page.locator('#cell'), page.locator('#bars'), series, 'fixture');
  } catch {
    caught = true;
  }
  assert(caught, 'checkUnmeasured passed a page that shows 0 for an unmeasured point: the check cannot fail');
});

for (const [who, email] of [['analyst', ANALYST], ['officer', OFFICER]]) {
  journey(`every client, ${who}: thread, case focus, client file views and portfolio row all land on the same client`, async ({ page }) => {
    await signIn(page, email);
    const borrowers = await api(page, '/borrowers');
    assert(borrowers.length >= 20, `expected the whole seeded book, found ${borrowers.length} clients`);
    for (const b of borrowers) {
      await page.goto(`${BASE}/clients/${b.code}`);
      await page.getByRole('heading', { level: 1, name: b.name }).waitFor();
      assert((await page.getByRole('alert').count()) === 0, `${b.name}: the thread shows an error`);
      const thread = await api(page, `/threads/${b.id}`);
      const text = await page.locator('.sq-messages').innerText(); // the heading is up, so the list must be there
      for (const other of borrowers) {
        if (other.id !== b.id && other.name.length > 12 && text.includes(other.name)) throw new Error(`${b.name}'s thread names ${other.name}`);
      }
      const open = thread.messages.filter((m) => (m.type === 'case' || m.type === 'ask') && m.status === 'open');
      for (const m of open.slice(0, 2)) {
        await page.goto(`${BASE}/clients/${b.code}?case=${m.work_item_id}`);
        const card = page.locator(`[data-work-item="${m.work_item_id}"][data-focused="true"]`);
        await card.waitFor();
        if (m.type === 'case') {
          // a case opens CasePanel: its decision form is there exactly when the server permits a decision
          const view = await api(page, `/cases/${m.work_item_id}`);
          const decide = await card.getByRole('button', { name: 'Record decision' }).count();
          assert((decide > 0) === view.decisions.some((d) => d.permitted), `${b.name}: the decision form disagrees with the server for ${m.title}`);
        } else {
          // an ask renders its options: enabled exactly when the server says it needs this viewer
          const enabled = await card.locator('fieldset.sq-options:not([disabled])').count();
          assert((enabled > 0) === m.needs_you, `${b.name}: the ask's options disagree with the server for ${m.title}`);
        }
      }
      for (const v of VIEWS) {
        await page.goto(`${BASE}/clients/${b.code}/file${v}`);
        await page.getByRole('heading', { level: 1, name: b.name }).waitFor();
        assert((await page.getByRole('alert').count()) === 0, `${b.name}: client file${v || ' overview'} shows an error`);
      }
      await page.goto(`${BASE}/clients/${b.code}/file`);
      const measure = page.locator('[data-measure]');
      await measure.waitFor();
      await checkUnmeasured(measure.locator('[data-measure-now]'), measure, await api(page, `/borrowers/${b.id}/measure`), `${b.code} overview`);
    }
    await page.goto(`${BASE}/portfolio`);
    await page.locator('[data-ready]').waitFor(); // the table is drawn only once the portfolio has loaded
    const portfolio = await api(page, '/me/portfolio');
    for (const row of portfolio.sections.flatMap((s) => s.rows)) {
      const tr = page.locator(`tr[data-borrower="${row.code}"]`);
      assert((await tr.count()) === 1, `${row.name} is not on My Portfolio exactly once`);
      await checkUnmeasured(tr.locator('[data-measure-cell]'), tr, row.measure, `portfolio ${row.code}`);
    }
  });
}

for (const [who, email] of [['analyst', ANALYST], ['officer', OFFICER]]) {
  journey(`the ${who}'s briefing lists each thing once and prints no raw amount in a title`, async ({ page }) => {
    await signIn(page, email);
    const { b } = await record(page);
    const keys = b.items.map((i) => i.key);
    assert(new Set(keys).size === keys.length, 'a briefing row is listed twice');
    const raw = b.items.filter((i) => /\d{1,3}(,\d{3})+\.\d{2}\b/.test(i.title));
    assert(raw.length === 0, `raw amounts in titles: ${raw.map((i) => i.title).join('; ')}`);
  });
}

/** Every Squad screen a person of this kind can reach; the contrast and width journeys walk all of them. */
async function screensFor(page, kind) {
  const [b] = await api(page, '/borrowers');
  const shared = ['/', `/clients/${b.code}`, `/clients/${b.code}/file`, `/clients/${b.code}/file/spreads`, `/clients/${b.code}/file/covenants`, `/clients/${b.code}/file/documents`, `/clients/${b.code}/file/packages`, `/clients/${b.code}/file/runs`, `/clients/${b.code}/file/loans`, '/portfolio', '/review-room'];
  if (kind === 'officer') return [...shared, '/approvals'];
  if (kind === 'admin') return ['/', '/oversight', '/oversight/activity', '/oversight/ledger', '/oversight/governance', '/oversight/evaluations', '/oversight/clock'];
  return shared;
}

const PEOPLE = [['analyst', ANALYST], ['officer', OFFICER], ['admin', 'admin@bankofstoic.example']];

journey('every look, every Squad screen, every role: contrast and names hold', async ({ browser }) => {
  for (const [kind, email] of PEOPLE) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    await signIn(page, email);
    const screens = await screensFor(page, kind);
    for (const look of LOOKS) {
      await page.goto(`${BASE}/`);
      await page.getByRole('button', { name: /^look:/i }).click();
      await page.getByRole('menuitemradio', { name: look }).click();
      for (const path of screens) {
        await page.goto(`${BASE}${path}`);
        await page.locator('.sq-main').waitFor();
        await page.addScriptTag({ content: axeSource });
        const result = await page.evaluate(() => window.axe.run(document.body, { runOnly: ['color-contrast', 'label', 'button-name', 'link-name'] }));
        const bad = result.violations.map((v) => `${v.id}: ${v.nodes.length}`);
        assert(bad.length === 0, `${kind} ${look} ${path}: ${bad.join(', ')}`);
      }
    }
    await context.close();
  }
});

journey('every width from 1000 to 1920 on every Squad screen and role: no horizontal scroll', async ({ browser }) => {
  for (const [kind, email] of PEOPLE) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    await signIn(page, email);
    const screens = await screensFor(page, kind);
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      for (const path of screens) {
        await page.goto(`${BASE}${path}`);
        await page.locator('.sq-main').waitFor();
        await noScroll(page, `${kind} ${path} at ${width}px`);
      }
    }
    await context.close();
  }
});


journey('the administrator sees Oversight and no credit decision anywhere', async ({ page }) => {
  await signIn(page, 'admin@bankofstoic.example');
  await page.goto(`${BASE}/oversight`);
  await page.getByRole('navigation', { name: 'Oversight' }).waitFor();
  const items = (await api(page, '/work-items')).slice(0, 3);
  for (const w of items) {
    const b = await api(page, `/borrowers/${w.borrower_id}`);
    await page.goto(`${BASE}/clients/${b.code}?case=${w.id}`);
    await page.locator(`[data-work-item="${w.id}"][data-focused="true"]`).waitFor();
    assert((await page.getByRole('button', { name: /record decision|^send to|^return to|^attach/i }).count()) === 0, 'an administrator was offered a credit action');
  }
});

mkdirSync(failuresDir, { recursive: true });
const browser = await chromium.launch({ headless: !process.env.HEADED });
let failed = 0;
const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null; // ONLY='every client' reruns just those journeys
for (const { name, fn } of journeys.filter((j) => !only || only.test(j.name))) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  try {
    await fn({ page, browser });
    console.log(`PASS  ${name}`);
  } catch (error) {
    failed += 1;
    console.error(`FAIL  ${name}\n      ${error.message}`);
    await page.screenshot({ path: resolve(failuresDir, `${name.replace(/\W+/g, '-').slice(0, 60)}.png`) }).catch(() => {});
  }
  await context.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
