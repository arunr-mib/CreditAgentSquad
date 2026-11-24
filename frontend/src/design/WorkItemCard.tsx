import { ArrowUpRight, ChevronDown, Users } from 'lucide-react';
import { DropdownMenu } from 'radix-ui';
import type { ReactNode } from 'react';
import type { Decision, EvidenceLink } from '@/api/types';
import { cx } from '@/lib/cx';
import { Button } from './Button';
import { Card } from './Card';
import { ProvenanceGlyph } from './ProvenanceGlyph';
import { StatusDot, type StatusTone } from './StatusDot';

export interface WorkItemCardProps {
  /** Plain-words type, for example "Covenant breach, certificate reports compliant". */
  typeLabel: string;
  /** Identifier of the work item, shown in the mono face. */
  itemId: string;
  severity: { tone: StatusTone; label: string };
  /** The item is a covenant breach: its type is marked in red. Severity itself never uses red. */
  breach?: boolean;
  subject: string;
  context?: string;
  /** For example "Due today" or "Overdue 3 days". */
  due?: { text: string; attention?: boolean };
  /** One specific question for a person. */
  question: string;
  evidence: EvidenceLink[];
  decisions: Decision[];
  onDecide?: (decision: Decision) => void;
  requiresSecondPerson?: boolean;
  /** The agent's recommendation and guardrail notes, between the evidence and the decisions. */
  children?: ReactNode;
  className?: string;
  headingLevel?: 'h2' | 'h3';
}

/**
 * A question for a person: what is asked, the evidence, and the decisions allowed.
 * Exactly one decision is primary; the others sit behind "Other decisions". The card decides nothing itself.
 */
export function WorkItemCard({
  typeLabel,
  itemId,
  severity,
  breach,
  subject,
  context,
  due,
  question,
  evidence,
  decisions,
  onDecide,
  requiresSecondPerson,
  children,
  className,
  headingLevel: Heading = 'h3',
}: WorkItemCardProps) {
  const SubHeading = Heading === 'h2' ? 'h3' : 'h4';
  const primary = decisions.find((decision) => decision.primary);
  const others = decisions.filter((decision) => !decision.primary);
  return (
    <Card className={cx('flex flex-col', className)}>
      <div className="px-4 pt-3.5">
        <div className="flex items-center justify-between gap-3 text-caption">
          <StatusDot tone={severity.tone}>
            <span className={severity.tone === 'attention' ? 'font-medium' : undefined}>{severity.label}</span>
          </StatusDot>
          {due ? <span className={cx('tnum', due.attention ? 'font-medium text-amber' : 'text-ink-500')}>{due.text}</span> : null}
        </div>
        <div className="mt-2 text-caption text-ink-500">
          <span className="font-medium text-ink-700">{subject}</span>
          {context ? <> · {context}</> : null}
        </div>
        <Heading className="mt-1 text-title font-semibold text-pretty text-ink">{question}</Heading>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 text-caption text-ink-500">
          {breach ? (
            <StatusDot tone="breach" emphasis>
              {typeLabel}
            </StatusDot>
          ) : (
            <span>{typeLabel}</span>
          )}
          <span className="ident">{itemId}</span>
        </div>
      </div>

      <div className="mt-3.5 px-4">
        <SubHeading className="eyebrow mb-1">Evidence</SubHeading>
        <ul className="border-t border-ink">
          {evidence.map((item) => (
            <li key={`${item.label}-${item.ref ?? item.detail ?? ''}`} className="border-b border-hairline">
              <a href={item.href ?? '#'} className="group flex min-h-8 items-center gap-2 py-1 text-body text-ink t-colors hover:text-cobalt-strong">
                <ProvenanceGlyph kind={item.kind} className="group-hover:text-cobalt-strong" />
                <span className="min-w-0 flex-1">
                  <span className="font-medium">{item.label}</span>
                  {item.detail ? <span className="text-ink-500 group-hover:text-cobalt-strong">, {item.detail}</span> : null}
                </span>
                {item.ref ? <span className="ident shrink-0 text-caption text-ink-500">{item.ref}</span> : null}
                <ArrowUpRight size={12} aria-hidden className="shrink-0 text-ink-400 group-hover:text-cobalt-strong" />
              </a>
            </li>
          ))}
        </ul>
      </div>

      {children ? <div className="mt-4 space-y-4 px-4">{children}</div> : null}

      {/* Decisions stay in view while the card is read: one clear next action, always reachable. */}
      <div className="sticky bottom-0 mt-4 rounded-b-md border-t border-hairline-strong bg-surface px-4 pt-3 pb-2.5">
        {primary ? (
          <Button variant="primary" className="w-full" onClick={() => onDecide?.(primary)}>
            {primary.label}
          </Button>
        ) : null}
        <div className="mt-1.5 flex min-h-7 items-center justify-between gap-3">
          {requiresSecondPerson ? (
            <p className="flex items-center gap-1.5 text-caption whitespace-nowrap text-ink-700">
              <Users size={12} aria-hidden className="shrink-0 text-ink-500" />
              Needs a second approver
            </p>
          ) : (
            <span />
          )}
          {others.length > 0 ? (
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <Button variant="ghost" size="sm" className="-mr-2" iconRight={<ChevronDown size={13} aria-hidden />}>
                  Other decisions
                </Button>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  align="end"
                  side="top"
                  sideOffset={6}
                  className="anim-pop z-50 min-w-56 rounded-md border border-hairline-strong bg-surface p-1 shadow-raised"
                >
                  {others.map((decision) => (
                    <DropdownMenu.Item
                      key={decision.id}
                      onSelect={() => onDecide?.(decision)}
                      className="flex h-8 cursor-pointer items-center rounded-xs px-2 text-body text-ink outline-none select-none data-[highlighted]:bg-cobalt-bg"
                    >
                      {decision.label}
                    </DropdownMenu.Item>
                  ))}
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
