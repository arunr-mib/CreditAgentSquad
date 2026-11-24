import { Fragment, useState, type ReactNode } from 'react';
import type { GuardrailNote } from '@/api/types';
import { cx } from '@/lib/cx';
import { AgentMark } from './AgentMark';
import { Figure, useFacts } from './Figure';
import { StatusDot } from './StatusDot';

const FACT_REF = /\{\{fact:([A-Za-z0-9_.-]+)\}\}/g;

/**
 * Renders agent-written text. The agent never types a number: it writes {{fact:<id>}}
 * and this component renders the stored fact as a Figure, with its source one click away.
 * A reference to a fact that is not in scope is shown as an unresolved identifier, not hidden.
 */
export function AgentText({ text, className }: { text: string; className?: string }) {
  const { facts } = useFacts();
  const paragraphs = text.split(/\n{2,}/);
  return (
    <div className={cx('space-y-2.5 text-prose text-ink', className)}>
      {paragraphs.map((paragraph, pIndex) => {
        const parts: ReactNode[] = [];
        let last = 0;
        for (const match of paragraph.matchAll(FACT_REF)) {
          const start = match.index;
          if (start > last) parts.push(<Fragment key={`t${last}`}>{paragraph.slice(last, start)}</Fragment>);
          const fact = facts[match[1] ?? ''];
          parts.push(
            fact ? (
              <Figure key={`f${start}`} fact={fact} weight="medium" />
            ) : (
              <span key={`f${start}`} className="ident text-amber">
                unresolved {match[1]}
              </span>
            ),
          );
          last = start + match[0].length;
        }
        if (last < paragraph.length) parts.push(<Fragment key={`t${last}`}>{paragraph.slice(last)}</Fragment>);
        return <p key={pIndex}>{parts}</p>;
      })}
    </div>
  );
}

export interface AgentNoteProps {
  agent: string;
  /** What the agent did, in its voice: "Recommends escalate", "Drafted commentary". Never "Resolved". */
  headline?: string;
  /** Agent text with {{fact:<id>}} references, or custom content. */
  body?: string;
  children?: ReactNode;
  /** Agent writing is a draft until a person approves it. */
  state: 'draft' | 'approved';
  approvedBy?: string;
  /** Run identifier and time, shown in the footer. */
  runId?: string;
  writtenAt?: string;
  /** Show only the first paragraphs until the reader asks for the rest. For triage views. */
  collapseAfter?: number;
  className?: string;
}

/**
 * Agent-written text, marked in iris: a tinted ground, a hairline border on all four sides
 * and the agent mark. No coloured edge stripe.
 */
export function AgentNote({ agent, headline, body, children, state, approvedBy, runId, writtenAt, collapseAfter, className }: AgentNoteProps) {
  const [expanded, setExpanded] = useState(false);
  const paragraphs = body ? body.split(/\n{2,}/) : [];
  const collapsible = collapseAfter !== undefined && paragraphs.length > collapseAfter;
  const shown = collapsible && !expanded ? paragraphs.slice(0, collapseAfter).join('\n\n') : body;
  return (
    <section aria-label={`Written by ${agent}${headline ? `: ${headline}` : ''}`} className={cx('rounded-md border border-iris-border bg-iris-bg', className)}>
      <header className="flex items-center justify-between gap-3 px-4 pt-3">
        <span className="inline-flex items-center gap-1.5 text-caption font-semibold text-iris">
          <AgentMark />
          {agent}
        </span>
        <span className="text-caption">
          {state === 'draft' ? (
            <StatusDot tone="attention">Draft, not yet approved</StatusDot>
          ) : (
            <StatusDot tone="pass">Approved{approvedBy ? ` by ${approvedBy}` : ''}</StatusDot>
          )}
        </span>
      </header>
      <div className="px-4 pt-2 pb-3.5">
        {headline ? <p className="mb-1.5 text-title font-semibold text-ink">{headline}</p> : null}
        {shown ? <AgentText text={shown} /> : null}
        {collapsible ? (
          <button type="button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)} className="link mt-2 text-body font-medium">
            {expanded ? 'Show less' : 'Read the full note'}
          </button>
        ) : null}
        {children}
      </div>
      {runId || writtenAt ? (
        <footer className="flex items-center justify-between gap-3 border-t border-iris-border px-4 py-2 text-caption text-ink-700">
          <span>{writtenAt ? `Written ${writtenAt}` : null}</span>
          {runId ? (
            <span>
              Run <span className="ident">{runId}</span>
            </span>
          ) : null}
        </footer>
      ) : null}
    </section>
  );
}

const actionDot: Record<string, { tone: 'pass' | 'attention'; label: string }> = {
  passed: { tone: 'pass', label: 'Passed' },
  pass: { tone: 'pass', label: 'Passed' },
  changed: { tone: 'attention', label: 'Changed' },
  blocked: { tone: 'attention', label: 'Blocked' },
  refuse: { tone: 'attention', label: 'Refused' },
  refused: { tone: 'attention', label: 'Refused' },
  abstain: { tone: 'attention', label: 'Abstained' },
  retry: { tone: 'attention', label: 'Retried' },
  escalate: { tone: 'attention', label: 'Escalated' },
};

/** The API may record an action this list does not know yet: it is shown in its own words, as needing attention. */
function actionOf(action: string): { tone: 'pass' | 'attention'; label: string } {
  return actionDot[action] ?? { tone: 'attention', label: action.charAt(0).toUpperCase() + action.slice(1).replace(/_/g, ' ') };
}

/** What the guardrails checked after the agent answered, and anything they forced to change. */
export function GuardrailNotes({ notes, className, as: Heading = 'h4' }: { notes: GuardrailNote[]; className?: string; as?: 'h3' | 'h4' }) {
  return (
    <div className={className}>
      <Heading className="eyebrow mb-1">Guardrail checks</Heading>
      <ul className="border-t border-ink">
        {notes.map((note, index) => (
          <li key={`${note.layer}-${note.check}-${index}`} className="grid grid-cols-[1fr_auto] gap-x-4 border-b border-hairline py-1.5 text-caption">
            <span className="font-medium text-ink">{note.check.charAt(0).toUpperCase() + note.check.slice(1).replace(/_/g, ' ')}</span>
            <StatusDot tone={actionOf(note.action).tone}>{actionOf(note.action).label}</StatusDot>
            <span className="col-span-2 text-ink-700">{note.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
