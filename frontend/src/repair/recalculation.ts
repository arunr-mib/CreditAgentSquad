/**
 * What code did after a figure was corrected, rejected or keyed, in words.
 * Nothing here decides anything: it restates the API's `recalculation` summary, sentence by sentence.
 */
import type { CovenantRetest, Recalculation } from '@/api/schema';
import { humanize, outcomeOf, quarterLabel } from '@/domain/labels';

const plural = (count: number, one: string, many: string) => (count === 1 ? one : many);

/** A covenant outcome in words; a test that did not exist before is said to be untested, not passed. */
export function outcomeLabel(outcome: string | null): string {
  if (!outcome) return 'Not tested before';
  return outcomeOf(outcome).label || humanize(outcome);
}

export interface CovenantChange {
  /** The covenant's name where known, otherwise its identifier in sentence case. */
  covenant: string;
  period: string;
  before: string | null;
  after: string;
  /** "Total Leverage Ratio, Q3 2026: Compliant → Breach" */
  sentence: string;
}

export interface RecalculationSummary {
  /** One sentence each: results retired, statement totals, review metrics, tests run again. */
  sentences: string[];
  /** Covenant tests whose outcome is different after the change. */
  changes: CovenantChange[];
  /** True when the corrected statements no longer foot: a person has a new question to answer. */
  needsAttention: boolean;
}

function change(test: CovenantRetest, names: Record<string, string>): CovenantChange {
  const covenant = names[test.covenant_id] ?? humanize(test.covenant_id);
  const period = quarterLabel(test.period_end);
  return { covenant, period, before: test.before, after: test.after, sentence: `${covenant}, ${period}: ${outcomeLabel(test.before)} → ${outcomeLabel(test.after)}` };
}

/**
 * `names` maps a covenant id to its name (the API returns only ids). `subject` is how the figure
 * is referred to: "the old figure" after a correction, "this figure" after a rejection.
 */
export function recalculationSummary(recalculation: Recalculation, names: Record<string, string> = {}, subject = 'the old figure'): RecalculationSummary {
  const sentences: string[] = [];
  const { retired, totals } = recalculation;
  const metrics = recalculation.metrics ?? [];
  const covenants = recalculation.covenants ?? [];

  if (retired > 0) {
    sentences.push(`${retired} ${plural(retired, 'result', 'results')} calculated from ${subject} ${plural(retired, 'was', 'were')} retired.`);
  }

  if (totals === 'recalculated') sentences.push('Statement totals were recalculated from the figures now on file, and the statements foot.');
  if (totals === 'does_not_foot') sentences.push('The statements no longer foot, so no totals are stored. That question is now in the work queue for a person.');
  if (totals === 'not_recalculated') sentences.push('Statement totals were not recalculated: the length of the period could not be worked out.');

  const measured = metrics.filter((metric) => metric.fact_id).length;
  const unmeasured = metrics.length - measured;
  if (measured > 0) sentences.push(`${measured} review ${plural(measured, 'metric was', 'metrics were')} calculated again.`);
  if (unmeasured > 0) {
    sentences.push(`${unmeasured} review ${plural(unmeasured, 'metric', 'metrics')} could not be measured from the figures on file and ${plural(unmeasured, 'stays', 'stay')} absent.`);
  }

  const changed = covenants.filter((test) => test.before !== test.after);
  const same = covenants.length - changed.length;
  if (same > 0) sentences.push(`${same} covenant ${plural(same, 'test was', 'tests were')} run again with the same outcome.`);
  if (changed.length > 0) {
    sentences.push(`${changed.length} covenant ${plural(changed.length, 'outcome', 'outcomes')} changed. Earlier decisions and commentary used the old ${plural(changed.length, 'outcome', 'outcomes')}.`);
  }

  if (sentences.length === 0) sentences.push(`Nothing had been calculated from ${subject}, so nothing was retired or recalculated.`);

  return { sentences, changes: changed.map((test) => change(test, names)), needsAttention: totals === 'does_not_foot' || totals === 'not_recalculated' };
}
