// frontend/e2e/hosted-smoke.mjs
// Smoke test for a deployment: sign-in for every demo role, every Squad screen per role with no failed
// request, a source PDF, the ledger check, agents on/off as expected (and, when off, every composer saying
// so before anyone types), setup routes hidden, and (HANDOFF=1) the Approvals hand-off, which writes.
// Usage: BASE_URL=https://<host> [EXPECT_MODEL=off|on] [HANDOFF=1] pnpm e2e:smoke
// For the controller and the owner's own walk-through. No tracing, no video: nothing about the session
// is kept except failure screenshots (frontend/e2e/failures/, git-ignored).
// Not strictly read-only: every sign-in adds a session and a ledger event, and a wrong SQUAD_DEMO_PASSWORD
// records 9 failed sign-ins (which can lock the accounts for a while). A frozen site's host is refused.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { refuseFrozenHost } from './frozen-hosts.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL?.replace(/\/$/, '');
if (!BASE) { console.error('set BASE_URL'); process.exit(2); }
refuseFrozenHost(BASE);
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const EXPECT_MODEL = (process.env.EXPECT_MODEL ?? 'off') === 'on';
const OUT = process.env.SMOKE_OUT ?? '/tmp/claude-0/hosted-smoke';
const failuresDir = resolve(dirname(fileURLToPath(import.meta.url)), 'failures');
const ANALYST = 'priya.raman@bankofstoic.example';
const OFFICER = 'helen.strand@bankofstoic.example';
const ROLES = [
  ['analyst', ANALYST], ['analyst', 'tomas.keller@bankofstoic.example'],
  ['manager', 'dana.whitfield@bankofstoic.example'], ['manager', 'marcus.oyelaran@bankofstoic.example'],
  ['officer', OFFICER], ['admin_credit', 'li.zhang@bankofstoic.example'],
  ['admin_credit', 'omar.haddad@bankofstoic.example'], ['review', 'ruth.calloway@bankofstoic.example'],
  ['admin', 'admin@bankofstoic.example'],
];
// one innovation client (it carries Squad's demo question) and one kept C&I client, so both templates' screens load
const CLIENTS = ['cindrel-tech', 'kestrel-bay-packaging'];
const HEARTBEAT = '/api/v1/ledger/head';
let failed = 0;
const check = (ok, name, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : `  ${detail}`}`); if (!ok) failed += 1; };

function screens(kind, code) {
  if (kind === 'admin') return ['/', '/oversight', '/oversight/activity', '/oversight/ledger', '/oversight/governance', '/oversight/evaluations', '/oversight/clock'];
  const views = ['', '/spreads', '/covenants', '/documents', '/funding', '/loans', '/reviews', '/packages', '/runs', '/history'];
  const shared = ['/', `/clients/${code}`, ...views.map((v) => `/clients/${code}/file${v}`), '/portfolio', '/review-room'];
  return kind === 'officer' ? [...shared, '/approvals'] : shared;
}

async function signIn(browser, email) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  await page.goto(`${BASE}/sign-in`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(`${BASE}/`, { timeout: 60_000 });
  // counted from here: before sign-in the page rightly asks /auth/me and is told 401. `open` lets each screen go
  // quiet before the next opens, so an API request the browser abandons on navigation (net::ERR_ABORTED) was still
  // running then: on a cold start exactly the slow call to catch. Only the heartbeat, which polls for ever, may be
  // abandoned.
  const bad = [];
  page.on('requestfailed', (r) => {
    if (!r.url().startsWith(BASE)) return;
    const abandoned = r.failure()?.errorText === 'net::ERR_ABORTED';
    if (!abandoned || (r.url().includes('/api/v1/') && !r.url().includes(HEARTBEAT))) bad.push(`${r.method()} ${r.url()} ${r.failure()?.errorText}`);
  });
  page.on('response', (r) => { if (r.url().startsWith(BASE) && r.status() >= 400) bad.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
  return { context, page, bad };
}
const api = async (page, path, init) => {
  const r = await page.request.fetch(`${BASE}/api/v1${path}`, init);
  return { status: r.status(), body: r.headers()['content-type']?.includes('json') ? await r.json() : await r.body(), headers: r.headers() };
};
async function open(page, path) {
  await page.goto(`${BASE}${path}`);
  await page.locator('.sq-main').first().waitFor({ timeout: 60_000 });
  await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {}); // the heartbeat may keep it busy
}

/** Every composer (home, a client thread, a case) says the server's reason and offers no Ask, before anyone types. */
async function composersSayOff(page, reason, borrowers) {
  await open(page, '/');
  await checkComposer(page, 'home', page.getByRole('textbox', { name: 'Ask Squad about the whole portfolio' }), reason);
  const id = borrowers.find((b) => b.code === CLIENTS[0]);
  await open(page, `/clients/${id.code}`);
  await checkComposer(page, 'thread', page.getByRole('textbox', { name: `Ask Squad about ${id.name}` }), reason);
  const item = (await api(page, '/me/briefing')).body.items.find((i) => i.needs_you && i.work_item_id && i.kind !== 'question');
  if (!item) { check(false, 'case composer', 'no open case needs the analyst'); return; }
  await open(page, `/clients/${item.borrower_code}?case=${item.work_item_id}`);
  const card = page.locator(`[data-work-item="${item.work_item_id}"][data-focused="true"]`);
  await card.locator('summary', { hasText: 'Ask Squad about this case' }).click();
  await checkComposer(page, 'case', card.getByRole('textbox', { name: 'Ask Squad about this case' }), reason);
}
async function checkComposer(page, where, box, reason) {
  await box.waitFor({ timeout: 30_000 });
  const form = box.locator('xpath=ancestor::form[1]');
  // off: the box stays in the tab order (read-only, aria-disabled) so its reason is announced; Ask is disabled
  const disabled = (await box.getAttribute('aria-disabled')) === 'true' && (await box.getAttribute('readonly')) !== null;
  const askOff = await form.getByRole('button', { name: 'Ask' }).isDisabled();
  const says = (await form.innerText()).includes(reason);
  check(EXPECT_MODEL ? !disabled : disabled && askOff && says, `${where} composer ${EXPECT_MODEL ? 'is open' : 'says agents are off before anyone types'}`,
    JSON.stringify({ disabled, askOff, says }));
}

const browser = await chromium.launch({ headless: true });
mkdirSync(failuresDir, { recursive: true });
mkdirSync(OUT, { recursive: true });
const timings = {};

// what anyone can reach without signing in
{
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  check((await p.request.get(`${BASE}/api/_setup/status`)).status() === 404, 'setup routes are hidden without the token');
  check((await p.request.get(`${BASE}/api/v1/me/briefing`)).status() === 401, 'the API refuses a person who has not signed in');
  for (const path of ['/docs', '/openapi.json', '/api/docs', '/api/openapi.json']) {
    const r = await p.request.get(`${BASE}${path}`);
    const text = r.status() === 200 ? await r.text() : '';
    check(!/swagger|"openapi"/i.test(text), `${path} serves no API documentation`, `${r.status()}`);
  }
  await ctx.close();
}

for (const [kind, email] of ROLES) {
  let session;
  try {
    session = await signIn(browser, email);
    const { context, page, bad } = session;
    const cookie = (await context.cookies()).find((c) => c.httpOnly);
    check(Boolean(cookie?.secure), `${email}: session cookie is Secure and HttpOnly`, JSON.stringify({ secure: cookie?.secure, httpOnly: cookie?.httpOnly }));
    const borrowers = (await api(page, '/borrowers')).body;
    check(Array.isArray(borrowers) && borrowers.length === 20, `${email}: 20 clients`, `${borrowers?.length}`);
    for (const code of CLIENTS) {
      if (kind === 'admin' && code !== CLIENTS[0]) continue;
      for (const path of screens(kind, code)) {
        await open(page, path);
        const headings = await page.locator('h1').count();
        if (headings === 0) check(false, `${email} ${path}: has a heading`);
      }
    }
    check(true, `${email}: every screen has a heading`);
    check(bad.length === 0, `${email}: no failed request on any screen`, bad.slice(0, 5).join(' | '));
    if (kind === 'analyst' || kind === 'officer') {
      timings[email] = [];
      for (let i = 0; i < 5; i += 1) { const t = Date.now(); await api(page, '/me/briefing'); timings[email].push(Date.now() - t); }
    }
    if (email === ANALYST) {
      const id = borrowers.find((b) => b.code === CLIENTS[0]).id;
      const docs = (await api(page, `/borrowers/${id}/documents`)).body;
      const pdf = await api(page, `/documents/${docs[0].id}/file`);
      const bytes = Buffer.from(pdf.body);
      check(pdf.status === 200 && pdf.headers['content-type']?.includes('pdf') && bytes.subarray(0, 5).toString() === '%PDF-', 'a source PDF is served');
      writeFileSync(resolve(OUT, 'source.pdf'), bytes);
      // Served is not seen: the owner's first walk had pages that "could not be drawn" while the bytes were fine.
      const isSheet = (d) => ['xlsx', 'csv'].includes(d.meta?.format);
      const aPdf = docs.find((d) => !isSheet(d));
      await open(page, `/clients/${CLIENTS[0]}/file/documents?document=${aPdf.id}&page=1`);
      const drawn = await page.locator('[data-source-drawer] [data-pdf-page="ready"]').first().waitFor({ timeout: 60_000 }).then(() => true, () => false);
      check(drawn, 'a source page is drawn in the browser', `document ${aPdf.file_name}`);
      const aSheet = docs.find(isSheet);
      if (aSheet) {
        await open(page, `/clients/${CLIENTS[0]}/file/documents?document=${aSheet.id}&page=1`);
        const shown = await page.locator('[data-source-drawer]').getByRole('region', { name: 'Sheet as received' }).waitFor({ timeout: 60_000 }).then(() => true, () => false);
        check(shown, 'a spreadsheet is shown as its stored text, not as a page', `document ${aSheet.file_name}`);
      }
      const ledger = (await api(page, '/ledger/verify')).body;
      check(ledger.ok === true && ledger.append_only_for_this_role === true, 'ledger verifies and is append-only for this role', JSON.stringify(ledger));
      const model = (await api(page, '/agents/status')).body;
      check(model.model_connected === EXPECT_MODEL, `agents are ${EXPECT_MODEL ? 'on' : 'off'}`, JSON.stringify(model));
      await composersSayOff(page, model.reason, borrowers);
    }
  } catch (error) {
    check(false, `${email}: walk`, error.message.split('\n')[0]);
    await session?.page.screenshot({ path: resolve(failuresDir, `smoke-${email.split('@')[0]}.png`) }).catch(() => {});
  }
  await session?.context.close();
}

if (process.env.HANDOFF === '1') {
  // Writes: Priya routes one of her covenant cases to Helen with her view; Helen sees it in Approvals with
  // that view. Run only on a book that will be rebuilt afterwards. Selectors follow e2e/squad.mjs's hand-off.
  const a = await signIn(browser, ANALYST);
  const o = await signIn(browser, OFFICER);
  try {
    // a breach on one of her clients that she may still send on (as e2e/squad.mjs's hand-off finds it)
    let item = null;
    for (const w of (await api(a.page, '/work-items?item_type=covenant.breach')).body.filter((x) => x.status === 'open' && !x.assigned_to)) {
      const c = (await api(a.page, `/cases/${w.id}`)).body;
      if (c.may_route) { item = { work_item_id: w.id, borrower_code: c.borrower.code }; break; }
    }
    if (!item) throw new Error('no open covenant breach the analyst may route');
    const view = `Smoke test ${new Date().toISOString().slice(11, 19)}: the breach is on the certificate; please decide.`;
    await open(a.page, `/clients/${item.borrower_code}?case=${item.work_item_id}`);
    const card = a.page.locator(`[data-work-item="${item.work_item_id}"][data-focused="true"]`);
    await card.getByLabel(/your view/i).waitFor();
    if (await card.getByLabel('Send to').count()) { // a list only when more than one person may decide
      const value = await card.locator('select option', { hasText: 'Helen Strand' }).first().getAttribute('value');
      await card.getByLabel('Send to').selectOption(value);
    }
    await card.getByLabel(/your view/i).fill(view);
    await card.getByRole('button', { name: /^Send to / }).click();
    await a.page.getByText(/with your view · recorded/).waitFor({ timeout: 60_000 });
    await open(o.page, `/approvals?case=${item.work_item_id}`);
    await o.page.getByText(view).first().waitFor({ timeout: 60_000 });
    check(true, 'Approvals: the routed case reaches the officer with the analyst\'s view');
  } catch (error) {
    check(false, 'Approvals hand-off', error.message.split('\n')[0]);
    await a.page.screenshot({ path: resolve(failuresDir, 'smoke-handoff.png') }).catch(() => {});
  }
  await a.context.close();
  await o.context.close();
}

console.log(`TIMINGS ${JSON.stringify(timings)}`);
await browser.close();
console.log(failed ? `${failed} check(s) failed` : 'all checks passed');
process.exit(failed ? 1 : 0);
