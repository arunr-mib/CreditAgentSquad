// frontend/src/squad/__tests__/retired.test.ts
import { describe, expect, it } from 'vitest';

const sources = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
// Any string naming a retired module: an import, a dynamic import, or a vi.mock path.
const RETIRED = /['"]@\/(shell|drawer|fixtures)\/|['"]@\/screens\/(?!SignIn['"]|parts['"])/;

describe('the cockpit is retired', () => {
  it('the guard catches every way a file can name a retired module (it can fail)', () => {
    for (const sample of ["import { X } from '@/shell/AsOf';", "vi.mock('@/screens/work/WorkItemPanel', () => ({}));", "lazyRouteComponent(() => import('@/screens/Calendar'), 'Calendar')", "from '@/drawer/context'"]) {
      expect(RETIRED.test(sample), sample).toBe(true);
    }
    for (const sample of ["from '@/screens/SignIn'", "from '@/screens/parts'", "from '@/squad/case/parts'"]) {
      expect(RETIRED.test(sample), sample).toBe(false);
    }
  });

  it('no file lives where the cockpit lived, so a relative import of a restored file cannot pass', () => {
    const RETIRED_PATH = /^\/src\/(shell|drawer|fixtures)\/|^\/src\/screens\/(?!SignIn\.tsx$|parts\.tsx$)/;
    for (const sample of ['/src/shell/AppShell.tsx', '/src/drawer/context.tsx', '/src/screens/Portfolio.tsx', '/src/screens/borrower/Summary.tsx']) expect(RETIRED_PATH.test(sample), sample).toBe(true);
    for (const sample of ['/src/screens/SignIn.tsx', '/src/screens/parts.tsx', '/src/squad/shell/SquadShell.tsx']) expect(RETIRED_PATH.test(sample), sample).toBe(false);
    expect(Object.keys(sources).filter((path) => RETIRED_PATH.test(path))).toEqual([]);
  });

  it('no source file names the cockpit shell, drawer, fixtures or a cockpit screen', () => {
    const offenders = Object.entries(sources).filter(([path, text]) => !path.endsWith('retired.test.ts') && RETIRED.test(text)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it('the front-end label tables are gone: words come from the server', () => {
    const offenders = Object.entries(sources)
      .filter(([path, text]) => !path.endsWith('retired.test.ts') && /\b(docTypeLabel|DOC_TYPE_LABEL|signalLabel|SIGNAL_LABEL|describeEvent|decisionLabel|decisionHint|itemTypeLabel|actionLabel|permissionLabel|ROLES_WITH)\b/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  // Final review I4: a table of words written into the browser, of any name. Two or more `snake_case_key: 'Words'`
  // entries in a row (a value with a capital or a space: words, not an id) is a label table. Formats and ids are not
  // words ({ id: 'docx', label: 'Word' } has an id beside its label), so they do not match.
  // A record's own fields (label, title, hint...) are not keys of a table, and a value of class names is not words.
  const FIELDS = '(?:label|phrase|title|subject|detail|group|hint|keywords|text|sentence|name|description|note)';
  // a key, bare or in either quote; a value in either quote with a capital or a space (words), and no class names
  const KEY = String.raw`(?:\b|['"])(?!${FIELDS}\b)[a-z][a-z0-9_]*['"]?\s*:\s*`;
  const WORDS = String.raw`(?:'(?=[^']*(?:[A-Z]|\s))(?![^']*\b[a-z]+-[a-z0-9])[^'{}\n]+'|"(?=[^"]*(?:[A-Z]|\s))(?![^"]*\b[a-z]+-[a-z0-9])[^"{}\n]+")`;
  const LABEL_TABLE = new RegExp(`${KEY}${WORDS}\\s*,\\s*${KEY}${WORDS}`);
  // every source file of the browser; tests and their fixtures are not the product
  const SCANNED = /^\/src\/(?!test\/)(?!.*__tests__\/)(?!.*\.test\.tsx?$)/;

  it('the label-table guard can fail: it catches a table of words by its shape, whatever it is called', () => {
    for (const sample of [
      "const SEVERITY: Record<string, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };",
      "const READ = {\n  indexed: 'read page by page',\n  image_only: 'image only, with no readable text',\n};",
      "const words = { routed: 'sent this to', returned: 'returned this to', evidence_attached: 'attached a document' } as const;",
      "const FUNDING_KIND = { equity_round: 'Equity round', extension: 'Extension' };",
      // final re-review O3: quoted keys and double-quoted values are the same table
      "const STATUS = { 'needs_person': 'Needs a person', 'done': 'Done' };",
      'const SEV = { critical: "Critical", high: "High" };',
      'const STAGE = { "covenant_testing": "Covenant testing", "borrowing_base": "Borrowing base" };',
      "const MIX = { \"in_review\": 'In review', closed: \"Closed\" };",
    ]) expect(LABEL_TABLE.test(sample), sample).toBe(true);
    for (const sample of [
      "const FORMATS = [{ id: 'docx', label: 'Word' }, { id: 'xlsx', label: 'Excel' }];",
      "source.open({ type: 'document', documentId: d.id, page: 1, title: d.title });",
      "return { tone: 'pass', label: 'Verified by code' };",
      "{ type: 'record', kind: 'manual', title: 'Funding event', value: e.amount }",
      "{ id: 'home', group: 'Go to', label: 'Squad' }",
      "primary: 'bg-cobalt text-white border-transparent', secondary: 'bg-surface text-ink'",
    ]) expect(LABEL_TABLE.test(sample), sample).toBe(false);
  });

  it('no front-end file holds a table of words: every label is served by the server (backend/app/squad/words.py)', () => {
    const offenders = Object.entries(sources).filter(([path, text]) => SCANNED.test(path) && LABEL_TABLE.test(text)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
