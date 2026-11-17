import { describe, expect, it } from 'vitest';
import * as dec from '@/api/decimal';
import { breakdowns, cellThousands, covenants, facts, fccrRecommendation, named, periods, sourcePages, spreadSections } from './brightwater';
import { portfolioSummary, workItemFacts, workItems } from './workItems';

const value = (id: string | null | undefined) => {
  const fact = id ? facts[id] : undefined;
  if (!fact) throw new Error(`No fact ${id}`);
  return fact.value;
};

describe('Brightwater spread fixture', () => {
  it('balances at every period end', () => {
    for (const period of periods) {
      expect(cellThousands['bs.total_assets']?.[period.id as 'fy24']).toBe(cellThousands['bs.total_liabilities_and_equity']?.[period.id as 'fy24']);
    }
  });

  it('gives every cell a fact with provenance, or records the line as absent', () => {
    for (const section of spreadSections) {
      for (const group of section.groups) {
        for (const line of group.lines) {
          for (const period of periods) {
            const id = line.cells[period.id];
            if (id === null) continue;
            expect(facts[id ?? '']?.provenance.kind, `${line.key} ${period.id}`).toBeDefined();
          }
        }
      }
    }
  });

  it('foots: each computed line equals its stated total', () => {
    for (const section of spreadSections) {
      for (const line of section.groups.flatMap((group) => group.lines).filter((l) => l.computed)) {
        for (const period of periods) {
          expect(value(line.cells[period.id]), `${line.key} ${period.id}`).toBe(value(line.stated?.[period.id]));
        }
      }
    }
  });

  it('quotes the printed figure inside every extracted quote', () => {
    for (const fact of Object.values(facts)) {
      if (fact.provenance.kind === 'extracted') expect(fact.provenance.quote).toContain(fact.provenance.printed);
    }
  });

  it('has a source page for every extracted spread cell', () => {
    for (const fact of Object.values(facts)) {
      if (fact.provenance.kind === 'extracted' && /^(is|bs|stated)\./.test(fact.key)) {
        const page = sourcePages[`${fact.provenance.documentId}:${fact.provenance.page}`];
        expect(
          page?.rows.some((row) => row.factIds.includes(fact.id)),
          fact.id,
        ).toBe(true);
      }
    }
  });
});

describe('Brightwater covenant fixture', () => {
  it('tells the intended story: breach with the cap, pass as certified', () => {
    expect(named.fccr.value).toBe('1.12');
    expect(named.fccrCert.value).toBe('1.35');
    expect(dec.compare(named.fccr.value, named.fccrMin.value)).toBe(-1);
    expect(named.addback.value).toBe(named.addbackCap.value);
    // The certificate's ratio follows from the uncapped add-back.
    const uncapped = dec.add(named.fccrNumerator.value, dec.sub(named.chargeTtm.value, named.addback.value));
    expect(dec.div(uncapped, named.fccrDenominator.value, 2)).toBe(named.fccrCert.value);
    expect(dec.round(dec.add(named.adjEbitda.value, dec.sub(named.chargeTtm.value, named.addback.value)), 0)).toBe(named.certEbitda.value);
  });

  it('resolves every fact a covenant row and breakdown refers to', () => {
    for (const covenant of covenants) {
      for (const id of [covenant.calculatedFactId, covenant.thresholdFactId, covenant.headroomFactId, covenant.certificateFactId]) {
        expect(facts[id ?? '']).toBeDefined();
      }
      expect(breakdowns[covenant.id]?.rows.every((row) => facts[row.factId])).toBe(true);
    }
  });

  it('marks outcomes consistently with the calculated values', () => {
    for (const covenant of covenants) {
      const passes =
        covenant.operator === '>='
          ? dec.compare(value(covenant.calculatedFactId), value(covenant.thresholdFactId)) >= 0
          : dec.compare(value(covenant.calculatedFactId), value(covenant.thresholdFactId)) <= 0;
      expect(passes, covenant.id).toBe(!covenant.outcome.startsWith('breach'));
      const agrees = value(covenant.calculatedFactId) === value(covenant.certificateFactId);
      if (covenant.outcome === 'compliant') expect(agrees, covenant.id).toBe(true);
      if (covenant.outcome === 'compliant_variance') expect(agrees, covenant.id).toBe(false);
    }
  });
});

describe('agent text', () => {
  const recommendations = [fccrRecommendation, ...workItems.flatMap((item) => (item.recommendation ? [item.recommendation] : []))];

  it('never types a number: digits appear only inside fact references, dates and document references', () => {
    for (const recommendation of recommendations) {
      const stripped = recommendation.body.replace(/\{\{fact:[^}]+\}\}/g, '');
      expect(stripped, recommendation.runId).not.toMatch(/\d/);
    }
  });

  it('references only facts that are in scope', () => {
    for (const recommendation of recommendations) {
      for (const match of recommendation.body.matchAll(/\{\{fact:([^}]+)\}\}/g)) {
        expect(workItemFacts[match[1] ?? ''], `${recommendation.runId} ${match[1]}`).toBeDefined();
      }
    }
  });

  it('uses the allowed wording', () => {
    for (const recommendation of recommendations) {
      expect(recommendation.headline).not.toMatch(/^Resolved|AI thinks/i);
      expect(`${recommendation.headline} ${recommendation.body}`).not.toMatch(/\bfacility\b|\bwaive|\bamend the\b/i);
    }
  });
});

describe('work queue fixture', () => {
  it('is ordered by severity, then due date', () => {
    const rank = { critical: 0, high: 1, medium: 2, low: 3 };
    for (let i = 1; i < workItems.length; i += 1) {
      const a = workItems[i - 1];
      const b = workItems[i];
      if (!a || !b) continue;
      expect(rank[a.severity] < rank[b.severity] || (a.severity === b.severity && a.dueDate <= b.dueDate), `${a.id} before ${b.id}`).toBe(true);
    }
  });

  it('gives every item one question and exactly one primary decision', () => {
    for (const item of workItems) {
      expect(item.question.trim().length).toBeGreaterThan(20);
      expect(item.decisions.filter((decision) => decision.primary)).toHaveLength(1);
      expect(item.evidence.length).toBeGreaterThan(0);
    }
  });

  it('keeps the summary counts consistent', () => {
    const { cycles, borrowers, packages } = portfolioSummary;
    const inProgress = cycles.byState.filter((state) => state.label !== 'Closed').reduce((total, state) => total + state.count, 0);
    expect(inProgress).toBe(cycles.inProgress);
    expect(cycles.byState.reduce((total, state) => total + state.count, 0)).toBe(borrowers);
    expect(packages.byState.reduce((total, state) => total + state.count, 0)).toBe(borrowers);
    expect(new Set(workItems.map((item) => item.borrowerId)).size).toBe(cycles.byState[0]?.count);
  });
});
