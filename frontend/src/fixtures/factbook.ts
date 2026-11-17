import type { CalcInput, Fact, FactMap, FactStatus, Unit } from '@/api/types';

/**
 * Builds fixture facts with sequential identifiers, the way the backend would return them.
 * Fixture only: SYNTHETIC - FOR DEMONSTRATION. Lender: Bank of Stoic.
 */
export class FactBook {
  readonly facts: FactMap = {};
  private factSeq: number;
  private calcSeq: number;
  private readonly runId: string;

  constructor(options: { factStart: number; calcStart: number; runId: string }) {
    this.factSeq = options.factStart;
    this.calcSeq = options.calcStart;
    this.runId = options.runId;
  }

  private put(fact: Fact): Fact {
    this.facts[fact.id] = fact;
    return fact;
  }

  private nextFactId(): string {
    return `F-${this.factSeq++}`;
  }

  extracted(args: {
    key: string;
    label: string;
    value: string;
    unit?: Unit;
    periodLabel: string;
    documentId: string;
    documentTitle: string;
    page: number;
    quote: string;
    printed: string;
    labelText: string;
    scaleAsReported?: 1 | 1000;
    status?: FactStatus;
  }): Fact {
    return this.put({
      id: this.nextFactId(),
      key: args.key,
      label: args.label,
      value: args.value,
      unit: args.unit ?? 'usd',
      periodLabel: args.periodLabel,
      status: args.status ?? 'verified',
      provenance: {
        kind: 'extracted',
        documentId: args.documentId,
        documentTitle: args.documentTitle,
        page: args.page,
        quote: args.quote,
        printed: args.printed,
        labelText: args.labelText,
        scaleAsReported: args.scaleAsReported ?? 1,
        agentRunId: this.runId,
      },
    });
  }

  calculated(args: {
    key: string;
    label: string;
    value: string;
    unit?: Unit;
    periodLabel: string;
    formulaKey: string;
    formulaVersion: string;
    expression: string;
    inputs: CalcInput[];
    termsVersion?: string;
  }): Fact {
    return this.put({
      id: this.nextFactId(),
      key: args.key,
      label: args.label,
      value: args.value,
      unit: args.unit ?? 'usd',
      periodLabel: args.periodLabel,
      status: 'verified',
      provenance: {
        kind: 'calculated',
        calcId: `C-${this.calcSeq++}`,
        formulaKey: args.formulaKey,
        formulaVersion: args.formulaVersion,
        expression: args.expression,
        inputs: args.inputs,
        termsVersion: args.termsVersion,
      },
    });
  }

  system(args: { key: string; label: string; value: string; unit?: Unit; periodLabel: string; connector: string; recordRef: string; asOf: string }): Fact {
    return this.put({
      id: this.nextFactId(),
      key: args.key,
      label: args.label,
      value: args.value,
      unit: args.unit ?? 'usd',
      periodLabel: args.periodLabel,
      status: 'verified',
      provenance: { kind: 'system', connector: args.connector, recordRef: args.recordRef, asOf: args.asOf },
    });
  }

  manual(args: { key: string; label: string; value: string; unit?: Unit; periodLabel: string; enteredBy: string; enteredAt: string; reason: string }): Fact {
    return this.put({
      id: this.nextFactId(),
      key: args.key,
      label: args.label,
      value: args.value,
      unit: args.unit ?? 'usd',
      periodLabel: args.periodLabel,
      status: 'confirmed',
      provenance: { kind: 'manual', enteredBy: args.enteredBy, enteredAt: args.enteredAt, reason: args.reason },
    });
  }
}

/** Thousands as printed on a statement: 29480 → "29,480". */
export function printedThousands(thousands: number, parenthesised = false): string {
  const body = Math.abs(thousands).toLocaleString('en-US');
  return parenthesised ? `(${body})` : body;
}

/** Whole dollars as a decimal string from a figure reported in thousands. */
export function dollars(thousands: number): string {
  return String(thousands * 1000);
}
