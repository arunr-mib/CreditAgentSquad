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

  it('no source file names the cockpit shell, drawer, fixtures or a cockpit screen', () => {
    const offenders = Object.entries(sources).filter(([path, text]) => !path.endsWith('retired.test.ts') && RETIRED.test(text)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it('the front-end label tables are gone: words come from the server', () => {
    const offenders = Object.entries(sources)
      .filter(([path, text]) => !path.endsWith('retired.test.ts') && /\b(docTypeLabel|DOC_TYPE_LABEL|signalLabel|SIGNAL_LABEL|describeEvent)\b/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
