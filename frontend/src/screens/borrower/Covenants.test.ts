import { describe, expect, it } from 'vitest';
import type { CovenantTestRow } from '@/api/schema';
import { trendPoints } from './Covenants';

const row = (over: Partial<CovenantTestRow> & Pick<CovenantTestRow, 'id' | 'period_end'>): CovenantTestRow => ({
  borrower_id: 'b-1',
  facility_id: 'fac-1',
  cycle_id: null,
  covenant_id: 'lev',
  covenant_name: 'Total Leverage Ratio',
  calc_run_id: null,
  value_fact_id: null,
  threshold_fact_id: null,
  headroom_fact_id: null,
  reported_fact_id: null,
  value: '2.00',
  threshold: '2.50',
  operator: '<=',
  unit: 'ratio',
  passed: true,
  reported_value: null,
  reported_in_compliance: null,
  outcome: 'compliant',
  error: null,
  loan_name: null,
  terms_version: null,
  citation: null,
  work_item: null,
  ...over,
});

describe('the covenant trend', () => {
  it('carries each period’s own threshold, so a step-down draws as a step', () => {
    const points = trendPoints([
      row({ id: 'q1', period_end: '2026-03-31', value: '2.40', threshold: '2.75' }),
      row({ id: 'q2', period_end: '2026-06-30', value: '2.40', threshold: '2.50' }),
      row({ id: 'q3', period_end: '2026-09-30', value: '2.60', threshold: '2.50', passed: false }),
    ]);
    expect(points.map((point) => point.threshold)).toEqual([2.75, 2.5, 2.5]);
  });

  it('draws a point as a breach only when it failed against its own period’s threshold', () => {
    const points = trendPoints([
      // Above the later, lower threshold, but within the one in force at the time.
      row({ id: 'q1', period_end: '2026-03-31', value: '2.60', threshold: '2.75', passed: true }),
      row({ id: 'q3', period_end: '2026-09-30', value: '2.60', threshold: '2.50', passed: false }),
    ]);
    expect(points.map((point) => point.breach)).toEqual([false, true]);
  });

  it('leaves the threshold empty, not zero, where none was in force, and draws no breach there', () => {
    const points = trendPoints([
      row({ id: 'q1', period_end: '2026-03-31', threshold: null, passed: null }),
      row({ id: 'q2', period_end: '2026-06-30' }),
    ]);
    expect(points[0]?.threshold).toBeNull();
    expect(points[0]?.breach).toBe(false);
  });

  it('skips periods with no calculated value', () => {
    expect(trendPoints([row({ id: 'q1', period_end: '2026-03-31', value: null }), row({ id: 'q2', period_end: '2026-06-30' })])).toHaveLength(1);
  });
});
