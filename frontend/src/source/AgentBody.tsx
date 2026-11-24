import { Fragment, type ReactNode } from 'react';
import { useFactsById } from '@/api/hooks';
import { cx } from '@/lib/cx';
import { FactFigure } from './figures';

const FACT_REF = /\{\{fact:([A-Za-z0-9_.-]+)\}\}/g;

export function referencedFactIds(text: string): string[] {
  return [...text.matchAll(FACT_REF)].map((match) => match[1] ?? '').filter(Boolean);
}

/**
 * Agent-written text on real data. The agent never types a number: it writes {{fact:<id>}} and this
 * renders the stored fact as a figure that opens the source drawer. A reference that does not
 * resolve to a stored fact is shown as unresolved, never hidden and never replaced by a guess.
 */
export function AgentBody({
  text,
  className,
  chips,
}: {
  text: string;
  className?: string;
  /** Show each figure as a chip with its short fact id beside it. */ chips?: boolean;
}) {
  const ids = referencedFactIds(text);
  const facts = useFactsById(ids);
  return (
    <div className={cx('space-y-2.5 text-prose text-ink', className)}>
      {text.split(/\n{2,}/).map((paragraph, pIndex) => {
        const parts: ReactNode[] = [];
        let last = 0;
        for (const match of paragraph.matchAll(FACT_REF)) {
          const start = match.index;
          if (start > last) parts.push(<Fragment key={`t${last}`}>{paragraph.slice(last, start)}</Fragment>);
          const fact = facts.data?.[match[1] ?? ''];
          parts.push(
            fact ? (
              chips ? (
                <span
                  key={`f${start}`}
                  data-fact-chip
                  className="mx-px inline-flex items-baseline gap-1 rounded-xs border border-hairline-strong bg-surface px-1 align-baseline"
                >
                  <FactFigure fact={fact} weight="medium" />
                  <span className="ident text-micro text-ink-500">{fact.id.slice(0, 8)}</span>
                </span>
              ) : (
                <FactFigure key={`f${start}`} fact={fact} weight="medium" />
              )
            ) : facts.isPending && ids.length > 0 ? (
              <span key={`f${start}`} className="text-ink-500">
                …
              </span>
            ) : (
              <span key={`f${start}`} className="ident text-amber">
                unresolved {match[1]?.slice(0, 8)}
              </span>
            ),
          );
          last = start + match[0].length;
        }
        if (last < paragraph.length) parts.push(<Fragment key={`t${last}`}>{paragraph.slice(last)}</Fragment>);
        return (
          <p key={pIndex} className="whitespace-pre-line">
            {parts}
          </p>
        );
      })}
    </div>
  );
}
