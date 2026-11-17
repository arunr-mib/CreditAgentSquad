import { ArrowUpRight } from 'lucide-react';
import { Popover as RadixPopover } from 'radix-ui';
import { createContext, useContext, type ReactNode } from 'react';
import type { Fact, FactMap } from '@/api/types';
import { cx } from '@/lib/cx';
import { formatFigure, type FigureFormat } from './format';
import { popoverSurfaceClass } from './Popover';
import { provenance, ProvenanceGlyph } from './ProvenanceGlyph';
import { StatusDot } from './StatusDot';

/* ── Facts in scope ───────────────────────────────────────────────────── */

interface FactsContextValue {
  facts: FactMap;
  /** Where "open the source" goes for a fact. Screens supply this; the design system does not know routes. */
  sourceHref?: (fact: Fact) => string | undefined;
}

const FactsContext = createContext<FactsContextValue>({ facts: {} });

export function FactsProvider({ facts, sourceHref, children }: FactsContextValue & { children: ReactNode }) {
  return <FactsContext.Provider value={{ facts, sourceHref }}>{children}</FactsContext.Provider>;
}

export function useFacts(): FactsContextValue {
  return useContext(FactsContext);
}

/* ── Figure ───────────────────────────────────────────────────────────── */

export interface FigureProps extends FigureFormat {
  fact: Fact;
  /**
   * 'column' reserves the width of a closing parenthesis after positive values,
   * so digits line up with accounting negatives in a right-aligned column.
   */
  align?: 'inline' | 'column';
  weight?: 'regular' | 'medium' | 'semibold';
  /** Select the figure (for a side panel) instead of opening the source popover. */
  onSelect?: (fact: Fact) => void;
  selected?: boolean;
  /** For grids that manage a roving tab stop. */
  tabIndex?: number;
  className?: string;
}

const weights = { regular: 'font-regular', medium: 'font-medium', semibold: 'font-semibold' };

function accessibleName(fact: Fact, text: string): string {
  return `${text}, ${fact.label}, ${fact.periodLabel}. ${provenance[fact.provenance.kind].phrase}. Show source.`;
}

/**
 * A number, its unit, its provenance glyph, and the way to its source.
 * No figure is shown any other way: a bare number in JSX is a defect.
 */
export function Figure({ fact, align = 'inline', weight = 'regular', onSelect, selected, tabIndex, className, ...format }: FigureProps) {
  const { text, negative } = formatFigure(fact.value, fact.unit, format);
  const padParen = align === 'column' && fact.unit === 'usd' && !negative;

  const classes = cx(
    'group/figure -mx-1 inline-flex items-center gap-1 rounded-xs px-1 align-baseline text-ink t-colors',
    'hover:bg-cobalt-bg hover:text-cobalt-strong data-[state=open]:bg-cobalt-bg data-[state=open]:text-cobalt-strong',
    selected && 'bg-cobalt-bg text-cobalt-strong ring-1 ring-cobalt ring-inset',
    weights[weight],
    className,
  );

  const content = (
    <>
      <span className="tnum whitespace-nowrap">
        {text}
        {padParen ? <span className="invisible">)</span> : null}
      </span>
      <ProvenanceGlyph kind={fact.provenance.kind} className="group-hover/figure:text-cobalt-strong group-data-[state=open]/figure:text-cobalt-strong" />
    </>
  );

  if (onSelect) {
    return (
      <button
        type="button"
        aria-label={accessibleName(fact, text)}
        aria-pressed={selected}
        tabIndex={tabIndex}
        data-fact={fact.id}
        className={classes}
        onClick={() => onSelect(fact)}
      >
        {content}
      </button>
    );
  }

  return (
    <RadixPopover.Root>
      <RadixPopover.Trigger asChild>
        <button type="button" aria-label={accessibleName(fact, text)} tabIndex={tabIndex} className={classes}>
          {content}
        </button>
      </RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          side="bottom"
          align="end"
          sideOffset={6}
          collisionPadding={12}
          aria-label={`Source of ${fact.label}`}
          className={cx(popoverSurfaceClass, 'w-[380px]')}
        >
          <FactSource fact={fact} />
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}

/* ── Source of a fact ─────────────────────────────────────────────────── */

const statusDot: Record<Fact['status'], { tone: 'pass' | 'attention' | 'muted'; label: string }> = {
  verified: { tone: 'pass', label: 'Verified on the page' },
  confirmed: { tone: 'pass', label: 'Confirmed by a person' },
  proposed: { tone: 'attention', label: 'Proposed, not verified' },
  rejected: { tone: 'muted', label: 'Rejected' },
  superseded: { tone: 'muted', label: 'Superseded' },
};

/** A printed quote with the figure highlighted. A quote is prose in the interface face, never code. */
export function Quote({ text, highlight }: { text: string; highlight?: string }) {
  const index = highlight ? text.indexOf(highlight) : -1;
  return (
    <blockquote className="rounded-sm border border-hairline bg-canvas px-3 py-2 text-body text-ink-700">
      {index < 0 || !highlight ? (
        text
      ) : (
        <>
          {text.slice(0, index)}
          <mark className="tnum rounded-xs bg-cobalt-bg px-0.5 font-medium text-ink ring-1 ring-cobalt-border">{highlight}</mark>
          {text.slice(index + highlight.length)}
        </>
      )}
    </blockquote>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 text-caption">
      <dt className="shrink-0 text-ink-500">{label}</dt>
      <dd className="min-w-0 text-right text-ink">{children}</dd>
    </div>
  );
}

export interface FactSourceProps {
  fact: Fact;
  /** Hide the heading block when the surrounding panel already shows it. */
  bare?: boolean;
  /** Also hide the quote and document rows, when the page itself is shown beside this. */
  besidePage?: boolean;
}

/**
 * Shows where a figure came from: document, page and quoted text; or formula and inputs;
 * or the system record; or the person and their reason.
 */
export function FactSource({ fact, bare, besidePage }: FactSourceProps) {
  const { facts, sourceHref } = useFacts();
  const source = fact.provenance;
  const href = sourceHref?.(fact);
  const { text } = formatFigure(fact.value, fact.unit);
  const status = statusDot[fact.status];

  return (
    <div className={bare ? '' : 'p-4'}>
      {bare ? null : (
        <div className="mb-3 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="eyebrow flex items-center gap-1.5">
              <ProvenanceGlyph kind={source.kind} />
              {provenance[source.kind].phrase}
            </div>
            <div className="mt-1 text-body font-semibold text-ink">{fact.label}</div>
            <div className="text-caption text-ink-500">{fact.periodLabel}</div>
          </div>
          <div className="tnum shrink-0 text-heading font-semibold text-ink">{text}</div>
        </div>
      )}

      {source.kind === 'extracted' ? (
        <div className="space-y-2.5">
          {besidePage ? null : <Quote text={source.quote} highlight={source.printed} />}
          <dl className="space-y-1">
            {besidePage ? null : <Row label="Document">{source.documentTitle}</Row>}
            <Row label="Page">
              <span className="tnum">{source.page}</span>, printed as “{source.labelText}”
            </Row>
            {source.scaleAsReported === 1000 ? <Row label="Scale">Reported in thousands, stored in whole dollars</Row> : null}
            <Row label="Check">
              <StatusDot tone={status.tone}>{status.label}</StatusDot>
            </Row>
          </dl>
        </div>
      ) : null}

      {source.kind === 'calculated' ? (
        <div className="space-y-2.5">
          <p className="rounded-sm border border-hairline bg-canvas px-3 py-2 text-body text-ink-700">{source.expression}</p>
          <table className="w-full text-caption">
            <caption className="sr-only">Inputs to {fact.label}</caption>
            <thead>
              <tr className="border-b border-ink text-left">
                <th scope="col" className="eyebrow py-1 font-semibold">
                  Input
                </th>
                <th scope="col" className="eyebrow py-1 text-right font-semibold">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {source.inputs.map((input) => {
                const inputFact = facts[input.factId];
                return (
                  <tr key={input.factId} className="border-b border-hairline last:border-b-0">
                    <td className="py-1 pr-3 text-ink-700">
                      {input.op ? <span className="mr-1.5 inline-block w-2 text-center text-ink-500">{input.op}</span> : null}
                      {input.name}
                    </td>
                    <td className="py-1 text-right text-ink">
                      {inputFact ? (
                        <span className="inline-flex items-center gap-1">
                          <span className="tnum">{formatFigure(inputFact.value, inputFact.unit).text}</span>
                          <ProvenanceGlyph kind={inputFact.provenance.kind} labelled />
                        </span>
                      ) : (
                        <span className="ident text-ink-500">{input.factId}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <dl className="space-y-1">
            <Row label="Method">
              <span className="ident">{source.formulaKey}</span> · version <span className="ident">{source.formulaVersion}</span>
            </Row>
            {source.termsVersion ? <Row label="Terms in force">{source.termsVersion}</Row> : null}
          </dl>
        </div>
      ) : null}

      {source.kind === 'system' ? (
        <dl className="space-y-1">
          <Row label="System">{source.connector}</Row>
          <Row label="Record">
            <span className="ident">{source.recordRef}</span>
          </Row>
          <Row label="As of">{source.asOf}</Row>
        </dl>
      ) : null}

      {source.kind === 'manual' ? (
        <div className="space-y-2.5">
          <Quote text={source.reason} />
          <dl className="space-y-1">
            <Row label="Entered by">{source.enteredBy}</Row>
            <Row label="When">{source.enteredAt}</Row>
            <Row label="Check">
              <StatusDot tone={status.tone}>{status.label}</StatusDot>
            </Row>
          </dl>
        </div>
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-4 border-t border-hairline pt-2.5 text-caption">
        <span className="text-ink-500">
          {source.kind === 'calculated' ? 'Calculation ' : 'Fact '}
          <span className="ident text-ink-700">{source.kind === 'calculated' ? source.calcId : fact.id}</span>
        </span>
        {href ? (
          <a href={href} className="link inline-flex items-center gap-0.5 font-medium">
            {source.kind === 'extracted' ? `Open page ${source.page}` : source.kind === 'calculated' ? 'Open calculation' : 'Open record'}
            <ArrowUpRight size={12} aria-hidden />
          </a>
        ) : null}
      </div>
    </div>
  );
}
