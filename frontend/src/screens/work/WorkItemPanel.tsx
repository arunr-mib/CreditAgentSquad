import { Link } from '@tanstack/react-router';
import { ArrowUpRight, ShieldCheck, Users } from 'lucide-react';
import { useId, useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, errorMessage } from '@/api/client';
import { useAssignItem, useBorrowers, useDecide, useDocuments, useFactsById, useUsers, useWorkItem } from '@/api/hooks';
import type { ApiRecommendation, RelatedItem, WorkItemDetail } from '@/api/schema';
import type { ProvenanceKind } from '@/api/types';
import { useAuth } from '@/auth/context';
import {
  AgentMark,
  AgentNote,
  Button,
  Card,
  ChoiceCards,
  formatDate,
  formatDue,
  GuardrailNotes,
  ProvenanceGlyph,
  Quote,
  Select,
  Skeleton,
  StatusDot,
  Tag,
  useToast,
} from '@/design';
import {
  decisionHint,
  decisionLabel,
  decisionNeedsReason,
  docTypeLabel,
  formatTimestamp,
  humanize,
  isBreachItem,
  itemTypeLabel,
  permissionLabel,
  quarterLabel,
  roleLabel,
  ROLES_WITH,
  signalLabel,
  stageLabel,
} from '@/domain/labels';
import { useWorkspaceDrawer } from '@/drawer/context';
import { cx } from '@/lib/cx';
import { useAsOf } from '@/shell/AsOf';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import { FactFigure, SourcedFigure } from '@/source/figures';
import { ErrorNotice, Notice, SeverityTag, Textarea } from '../parts';
import { KeyFigures } from './KeyFigures';
import { HeldFigures } from './HeldFigures';

const text = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);

/* ── Evidence ─────────────────────────────────────────────────────────── */

function EvidenceRow({
  kind,
  label,
  detail,
  reference,
  children,
}: {
  kind: ProvenanceKind;
  label: string;
  detail?: string | null;
  reference?: string | null;
  children: ReactNode;
}) {
  return (
    <li className="flex min-h-8 items-center gap-2 border-b border-hairline py-1 text-body">
      <ProvenanceGlyph kind={kind} />
      <span className="min-w-0 flex-1 text-ink">
        <span className="font-medium">{label}</span>
        {detail ? <span className="text-ink-500">, {detail}</span> : null}
      </span>
      {reference ? <span className="ident shrink-0 text-caption text-ink-500">{reference}</span> : null}
      <span className="shrink-0">{children}</span>
    </li>
  );
}

const openClass = 'link inline-flex items-center gap-0.5 font-medium';

function Evidence({ item, code, headingLevel: Heading }: { item: WorkItemDetail; code: string | undefined; headingLevel: 'h3' | 'h4' }) {
  const source = useSource();
  const evidence = item.evidence;
  const valueId = text(evidence.value_fact_id);
  const reportedId = text(evidence.reported_fact_id);
  const calcId = text(evidence.calc_run_id);
  const testId = text(evidence.covenant_test_id);
  const reviewId = text(evidence.borrowing_base_review_id);
  const documentId = text(evidence.document_id);
  const subject = text(evidence.subject);
  const subjectDocument = subject?.startsWith('document:') ? subject.slice('document:'.length) : null;
  const signalId = text(evidence.signal_id);
  const missing = Array.isArray(evidence.missing) ? (evidence.missing as Array<{ document_type?: string; due_date?: string }>) : [];
  const lines = Array.isArray(evidence.lines)
    ? (evidence.lines as Array<{ line: string; computed: string | null; certificate: string | null; difference: string | null }>)
    : [];
  const basis = evidence.basis && typeof evidence.basis === 'object' ? (evidence.basis as Record<string, unknown>) : null;

  const facts = useFactsById([valueId, reportedId]);
  const documents = useDocuments(documentId || subjectDocument ? item.borrower_id : undefined);
  const filed = documents.data?.find((doc) => doc.id === documentId || (subjectDocument && doc.meta?.external_id === subjectDocument));

  const rows: ReactNode[] = [];
  if (valueId) {
    rows.push(
      <EvidenceRow key="value" kind="calculated" label="Calculated by code" detail={facts.data?.[valueId]?.label}>
        {facts.data ? <FactFigure fact={facts.data[valueId]} weight="semibold" /> : <Skeleton className="h-3 w-12" />}
      </EvidenceRow>,
    );
  }
  if (reportedId) {
    rows.push(
      <EvidenceRow key="reported" kind={facts.data?.[reportedId]?.kind ?? 'extracted'} label="Reported on the certificate">
        {facts.data ? <FactFigure fact={facts.data[reportedId]} /> : <Skeleton className="h-3 w-12" />}
      </EvidenceRow>,
    );
  }
  if (calcId) {
    rows.push(
      <EvidenceRow key="calc" kind="calculated" label="The calculation" detail="inputs and steps" reference={calcId.slice(0, 8)}>
        <button type="button" className={openClass} onClick={() => source.open({ type: 'calculation', id: calcId })}>
          Open
        </button>
      </EvidenceRow>,
    );
  }
  if (testId && code) {
    rows.push(
      <EvidenceRow key="test" kind="calculated" label="Covenant test" detail="breakdown, certificate comparison and trend">
        <Link to="/borrowers/$code/covenants" params={{ code }} search={{ test: testId }} className={openClass}>
          Open <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }
  if (reviewId && code) {
    rows.push(
      <EvidenceRow key="review" kind="calculated" label="Borrowing base review" detail="each line beside the certificate">
        <Link to="/borrowers/$code/borrowing-base" params={{ code }} search={{ review: reviewId }} className={openClass}>
          Open <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }
  if (documentId || subjectDocument) {
    const effective = text(evidence.effective_date);
    rows.push(
      <EvidenceRow
        key="document"
        kind="extracted"
        label={filed ? filed.title : 'Document on file'}
        detail={effective ? `effective ${formatDate(effective)}` : filed ? docTypeLabel(filed.doc_type).toLowerCase() : null}
      >
        {filed ? (
          <button
            type="button"
            className={openClass}
            onClick={() => source.open({ type: 'document', documentId: filed.id, page: 1, title: filed.title, borrowerCode: code })}
          >
            Open
          </button>
        ) : documents.isPending ? (
          <Skeleton className="h-3 w-10" />
        ) : (
          <span className="text-caption text-ink-500">Not found on file</span>
        )}
      </EvidenceRow>,
    );
  }
  for (const [index, entry] of missing.entries()) {
    rows.push(
      <EvidenceRow
        key={`missing-${index}`}
        kind="system"
        label={docTypeLabel(entry.document_type)}
        detail={entry.due_date ? `was due ${formatDate(entry.due_date)}` : 'not received'}
      >
        <Link to="/calendar" className={openClass}>
          Calendar <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }
  if (signalId && code) {
    const rule = text(evidence.rule_id);
    rows.push(
      <EvidenceRow key="signal" kind="calculated" label={rule ? signalLabel(rule) : 'Signal'} detail={basis ? basisSentence(basis) : null}>
        <Link to="/borrowers/$code/signals" params={{ code }} className={openClass}>
          Signals <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }

  const note = text(evidence.note);
  const error = text(evidence.error);
  const draft = text(evidence.draft_email);
  const withheld = Array.isArray(evidence.withheld_sections)
    ? (evidence.withheld_sections as Array<{ section?: string; withheld_by?: string; reason?: string }>)
    : [];

  return (
    <div>
      <Heading className="eyebrow mb-1">Evidence</Heading>
      {rows.length > 0 ? <ul className="border-t border-ink">{rows}</ul> : null}
      {withheld.length > 0 ? (
        <div data-withheld-sections className="mt-3">
          <p className="text-body text-ink-700">
            {withheld.length === 1 ? 'One section was' : `${withheld.length} sections were`} withheld from the sheet. The agent&rsquo;s text failed a
            check, so it is not shown; write the section or approve the sheet without it.
          </p>
          <ul className="mt-1.5 border-t border-hairline">
            {withheld.map((entry, index) => (
              <li key={`${entry.section ?? 'section'}-${index}`} className="border-b border-hairline py-1.5 text-body">
                <span className="font-medium text-ink">{humanize(entry.section ?? 'Section')}</span>
                {entry.withheld_by ? <span className="text-ink-600"> · withheld by the {entry.withheld_by}</span> : null}
                {entry.reason ? <span className="block text-ink-600">{entry.reason}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {lines.length > 0 && calcId ? (
        <table className="mt-2 w-full text-body">
          <caption className="eyebrow pb-1 text-left">Lines that differ, USD thousands</caption>
          <thead>
            <tr className="text-left">
              <th scope="col" className="eyebrow border-b border-ink py-1 font-semibold">
                Line
              </th>
              <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                Recalculated
              </th>
              <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                Certificate
              </th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.line} className="border-b border-hairline last:border-b-0">
                <th scope="row" className="py-1 text-left font-regular text-ink-700">
                  {humanize(line.line)}
                </th>
                <td className="py-1 text-right">
                  <SourcedFigure
                    value={line.computed}
                    unit="usd"
                    kind="calculated"
                    label={`${humanize(line.line)}, recalculated`}
                    source={{ type: 'calculation', id: calcId }}
                    scale={1000}
                    unitMark={false}
                    align="column"
                  />
                </td>
                <td className="py-1 text-right">
                  <SourcedFigure
                    value={line.certificate}
                    unit="usd"
                    kind="extracted"
                    label={`${humanize(line.line)}, on the certificate`}
                    source={{ type: 'calculation', id: calcId }}
                    scale={1000}
                    unitMark={false}
                    align="column"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {error ? <p className="mt-2 text-body text-amber">{error}</p> : null}
      {note ? <p className="mt-2 text-caption text-pretty text-ink-500">{note}</p> : null}
      {rows.length === 0 && lines.length === 0 && !note && !draft ? (
        <p className="border-t border-ink pt-2 text-body text-ink-500">No evidence is attached to this item.</p>
      ) : null}
      {draft ? (
        <AgentNote agent="Intake Agent" headline="Drafted a chaser, not sent" state="draft" className="mt-3">
          <p className="text-body whitespace-pre-line text-ink">{draft}</p>
        </AgentNote>
      ) : null}
    </div>
  );
}

/** A signal's basis in a few plain words. Counts of days are not money; figures with facts are shown on the Signals tab. */
function basisSentence(basis: Record<string, unknown>): string | null {
  if (typeof basis.days_late === 'number') return `${basis.days_late} days late against a limit of ${String(basis.threshold)}`;
  if (typeof basis.past_due_days === 'number') return `${basis.past_due_days} days past due against a limit of ${String(basis.threshold)}`;
  const subject = text(basis.subject) ?? text(basis.metric);
  return subject ? humanize(subject).toLowerCase() : null;
}

/* ── Recommendation ───────────────────────────────────────────────────── */

const HEADLINE: Record<string, string> = {
  resolve: 'Recommends resolve',
  escalate: 'Recommends escalate',
  request: 'Recommends request',
  abstain: 'Abstains',
  draft: 'Drafted for approval',
};

function Recommendation({
  recommendation,
  item,
  headingLevel,
  code,
}: {
  recommendation: ApiRecommendation;
  item: WorkItemDetail;
  headingLevel: 'h3' | 'h4';
  code: string | undefined;
}) {
  const kind = text(recommendation.recommendation) ?? text(recommendation.kind) ?? '';
  const body = text(recommendation.explanation) ?? text(recommendation.body) ?? text(recommendation.text) ?? '';
  const agent = text(recommendation.agent) ?? text(recommendation.agent_name) ?? 'Covenant Agent';
  const runId = text(recommendation.run_id) ?? item.agent_run_id;
  const source = useSource();
  const claims = Array.isArray(recommendation.claims) ? recommendation.claims : [];
  const missing = Array.isArray(recommendation.missing_evidence)
    ? recommendation.missing_evidence.filter((entry): entry is string => typeof entry === 'string')
    : [];
  return (
    <>
      <AgentNote
        agent={agent}
        headline={text(recommendation.headline) ?? HEADLINE[kind] ?? humanize(kind)}
        state="draft"
        runId={runId ? runId.slice(0, 8) : undefined}
      >
        {body ? <AgentBody text={body} /> : null}
        {claims.length > 0 ? (
          <div className="mt-3">
            <p className="eyebrow mb-1">Quoted from documents, found on the page by code</p>
            <ul className="space-y-1.5">
              {claims.map((claim, index) => (
                <li key={index}>
                  {claim.text ? <p className="text-body text-ink">{claim.text}</p> : null}
                  {claim.quote ? <Quote text={claim.quote} /> : null}
                  {claim.document_id && claim.page ? (
                    <button
                      type="button"
                      className="link mt-0.5 text-caption font-medium"
                      onClick={() =>
                        source.open({
                          type: 'document',
                          documentId: claim.document_id as string,
                          page: claim.page as number,
                          quote: claim.quote,
                          title: 'Cited document',
                          borrowerCode: code,
                        })
                      }
                    >
                      Open page {claim.page}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {missing.length > 0 ? (
          <div className="mt-2">
            <p className="eyebrow">Evidence the agent says is missing</p>
            <ul className="mt-1 list-disc pl-5 text-body text-ink">
              {missing.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {runId ? (
          <Link to="/agent-activity" search={{ run: runId }} className="link mt-2 inline-block text-body font-medium">
            See the run, step by step
          </Link>
        ) : null}
      </AgentNote>
      {item.guardrail_notes.length > 0 ? <GuardrailNotes notes={item.guardrail_notes} as={headingLevel} /> : null}
    </>
  );
}

/* ── Related items ────────────────────────────────────────────────────── */

/**
 * Open questions on the same borrower that may change this item's result: an amendment not yet
 * approved into terms, held figures, a correction. Shown before the decision; it does not block it.
 */
export function RelatedItems({ items, headingLevel: Heading }: { items: RelatedItem[]; headingLevel: 'h3' | 'h4' }) {
  const drawer = useWorkspaceDrawer();
  const headingId = useId();
  if (items.length === 0) return null;
  return (
    <section data-related-items aria-labelledby={headingId} className="rounded-md border border-amber-border bg-amber-bg px-3 py-2.5">
      <Heading id={headingId} className="text-body font-semibold text-ink">
        <StatusDot tone="attention" className="whitespace-normal!">
          Open questions that may change this result
        </StatusDot>
      </Heading>
      <p className="mt-0.5 pl-[13px] text-caption text-pretty text-ink-700">
        {items.length === 1 ? 'This item is' : 'These items are'} still open. You can decide now; the result may change once{' '}
        {items.length === 1 ? 'it is' : 'they are'} settled.
      </p>
      <ul className="mt-1.5 space-y-1 pl-[13px]">
        {items.map((related) => (
          <li key={related.id} className="text-body">
            <button type="button" className="link text-left font-medium" onClick={() => drawer.openItem(related.id)}>
              {related.title}
            </button>
            <span className="text-ink-700">
              {' '}
              · {related.relation}
            </span>
            <span className="ident ml-1.5 text-caption text-ink-500">{related.id.slice(0, 8)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ── Decision ─────────────────────────────────────────────────────────── */

/** The server's refusal, named by what it means and shown in its own words. */
function refusalTitle(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'Not recorded: your role cannot decide this item';
    if (error.status === 409) return 'Not recorded: a second person is required';
    if (error.status === 422) return 'Not recorded: this decision is not allowed';
    if (error.status === 404) return 'Not recorded: the item no longer exists';
  }
  return 'Not recorded';
}

/**
 * Shown in place of a silent refusal: who may decide, and one press to send the item to them.
 * Routing assigns the item to a person who holds the permission; it is recorded in the ledger.
 */
function AuthorityGate({ item }: { item: WorkItemDetail }) {
  const { user, can } = useAuth();
  const users = useUsers();
  const assign = useAssignItem(item.id);
  const toast = useToast();
  const roles = ROLES_WITH[item.required_permission] ?? [];
  const holders = (users.data ?? []).filter((person) => roles.includes(person.role) && person.id !== user?.id);
  const [chosen, setChosen] = useState('');
  const target = holders.find((person) => person.id === chosen) ?? holders[0];
  const assignee = users.data?.find((person) => person.id === item.assigned_to);
  const routed = assignee && roles.includes(assignee.role);
  const roleNames = roles.map(roleLabel).join(' or ');

  return (
    <div data-authority-gate role="note" className="mt-3 rounded-md border border-ink bg-canvas px-3 py-2.5">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-body font-semibold text-ink">
        <Tag tone="gate" icon={<ShieldCheck size={12} strokeWidth={2} />}>
          {roleNames} sign-off
        </Tag>
        This decision is outside your authority
      </p>
      <p className="mt-1 text-body text-pretty text-ink-700">
        It needs permission to {permissionLabel(item.required_permission)}. Your role{user ? `, ${roleLabel(user.role)},` : ''} does not have it, so the
        decision cannot be recorded from here.
      </p>
      {routed ? (
        <p data-routed className="mt-2 text-body text-ink">
          <StatusDot tone="neutral">
            Routed to {assignee.name}, {assignee.title}
          </StatusDot>
        </p>
      ) : !can('manage_actions') ? (
        <p className="mt-2 text-caption text-ink-700">Your role cannot route items either. Ask a {roleNames.toLowerCase()} to open it.</p>
      ) : holders.length === 0 ? (
        <p className="mt-2 text-caption text-ink-700">
          {users.isPending ? 'Finding who may decide.' : `No ${roleNames.toLowerCase()} is on file to route this to.`}
        </p>
      ) : (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {holders.length > 1 ? (
            <Select
              label="Route to"
              hideLabel
              className="w-full sm:w-72"
              value={target?.id ?? ''}
              onValueChange={setChosen}
              options={holders.map((person) => ({ value: person.id, label: `${person.name}, ${person.title}` }))}
            />
          ) : null}
          <Button
            variant="primary"
            disabled={assign.isPending || !target}
            onClick={() =>
              target &&
              assign.mutate(
                { assigned_to: target.id },
                {
                  onSuccess: () =>
                    toast({
                      tone: 'pass',
                      title: `Routed to ${target.name}`,
                      description: 'The item now shows in their queue as assigned to them. The routing is in the ledger.',
                    }),
                },
              )
            }
          >
            {assign.isPending ? 'Routing' : `Route to ${holders.length > 1 ? roleNames.toLowerCase() : (target?.name ?? roleNames)} for sign-off`}
          </Button>
        </div>
      )}
      {assign.error ? (
        <Notice tone="attention" title="Not routed" className="mt-2">
          The server said: “{errorMessage(assign.error)}”
        </Notice>
      ) : null}
    </div>
  );
}

export function DecisionForm({ item }: { item: WorkItemDetail }) {
  const decide = useDecide(item.id);
  const { can } = useAuth();
  const toast = useToast();
  const { reasonDraft } = useWorkspaceDrawer();
  const [decision, setDecision] = useState<string>('');
  const [reason, setReason] = useState('');
  const [takenStamp, setTakenStamp] = useState<number | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const permitted = can(item.required_permission);

  // Text a person chose to carry over from a Copilot answer: appended once, with the run it came from.
  if (reasonDraft && reasonDraft.itemId === item.id && reasonDraft.stamp !== takenStamp) {
    setTakenStamp(reasonDraft.stamp);
    setReason((current) => (current.trim() ? `${current.trim()}\n\n${reasonDraft.text}` : reasonDraft.text));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!permitted) return;
    if (!decision) {
      setProblem('Choose a decision first.');
      return;
    }
    if (decisionNeedsReason(decision) && !reason.trim()) {
      setProblem('This decision needs a reason. It is recorded in the ledger with your name.');
      return;
    }
    setProblem(null);
    decide.mutate(
      { decision, reason: reason.trim() },
      {
        onSuccess: () =>
          toast({
            tone: 'pass',
            title: `Recorded: ${decisionLabel(decision)}`,
            description: `${item.borrower_name ?? 'The item'} leaves the queue. The decision is in the ledger.`,
          }),
      },
    );
  }

  return (
    <form onSubmit={submit} noValidate aria-label="Record a decision" className="rounded-b-md border-t border-hairline-strong bg-surface px-4 pt-3 pb-4">
      <p className="eyebrow mb-1.5">{permitted ? 'Your decision' : 'The decision'}</p>
      <ChoiceCards
        label="Decision"
        value={decision}
        disabled={!permitted}
        onValueChange={(value) => {
          setDecision(value);
          setProblem(null);
          decide.reset();
        }}
        choices={item.allowed_decisions.map((option) => ({ value: option, label: decisionLabel(option), hint: decisionHint(option) || undefined }))}
      />
      {permitted ? (
        <Textarea
          className="mt-3"
          label={decision && decisionNeedsReason(decision) ? 'Reason (required)' : 'Reason'}
          hint="Recorded in the ledger with your name and the time."
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          rows={3}
        />
      ) : (
        <AuthorityGate item={item} />
      )}
      {problem ? (
        <p role="alert" className="mt-2 text-body font-medium text-amber">
          {problem}
        </p>
      ) : null}
      {decide.error ? (
        <Notice tone="attention" title={refusalTitle(decide.error)} className="mt-3">
          The server said: “{errorMessage(decide.error)}”
        </Notice>
      ) : null}
      <Button type="submit" variant="primary" className="mt-3 w-full" disabled={decide.isPending || !permitted}>
        {decide.isPending ? 'Recording' : 'Record decision'}
      </Button>
      {item.requires_second_person ? (
        <p className="mt-2 flex items-center gap-1.5 text-caption text-ink-700">
          <Users size={12} aria-hidden className="shrink-0 text-ink-500" />
          Needs a second person: whoever prepared this cannot approve it.
        </p>
      ) : null}
    </form>
  );
}

function RecordedDecision({ item }: { item: WorkItemDetail }) {
  const users = useUsers();
  const who = users.data?.find((user) => user.id === item.decided_by);
  return (
    <div className="rounded-b-md border-t border-hairline-strong px-4 pt-3 pb-3.5">
      <p className="eyebrow mb-1">Decision on record</p>
      <p className="text-title font-semibold text-ink">
        <StatusDot tone="pass">{decisionLabel(item.decision) || humanize(item.status)}</StatusDot>
      </p>
      <p className="mt-0.5 text-body text-ink-700">
        {who ? `${who.name}, ${who.title}` : 'A person'} · {formatTimestamp(item.decided_at)}
      </p>
      {item.decision_reason ? (
        <blockquote className="mt-2 rounded-sm border border-hairline bg-canvas px-3 py-2 text-body text-ink-700">{item.decision_reason}</blockquote>
      ) : null}
      <Link to="/governance" search={{ tab: 'ledger', entity: item.id }} className="link mt-2 inline-flex items-center gap-0.5 text-body font-medium">
        See it in the ledger <ArrowUpRight size={12} aria-hidden />
      </Link>
    </div>
  );
}

/* ── Panel ────────────────────────────────────────────────────────────── */

export interface WorkItemPanelProps {
  itemId: string;
  headingLevel?: 'h2' | 'h3';
  className?: string;
  /** In the workspace drawer the panel has no frame of its own. */
  variant?: 'card' | 'drawer';
}

/**
 * One question for a person: what is asked, the evidence (each row opens its source), what the
 * agent recommends if it said anything, and the decision. The panel decides nothing itself.
 */
export function WorkItemPanel({ itemId, headingLevel: Heading = 'h2', className, variant = 'card' }: WorkItemPanelProps) {
  const query = useWorkItem(itemId);
  const borrowers = useBorrowers();
  const { asOf } = useAsOf();
  const drawer = useWorkspaceDrawer();
  const SubHeading = Heading === 'h2' ? 'h3' : 'h4';

  if (query.error) return <ErrorNotice error={query.error} what="This item" onRetry={() => void query.refetch()} />;
  if (!query.data) {
    return (
      <Card role="status" aria-label="Loading the item" className={cx('space-y-3 px-4 py-4', className)}>
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-24 w-full" />
      </Card>
    );
  }

  const item = query.data;
  const borrower = borrowers.data?.find((row) => row.id === item.borrower_id);
  const due = item.due_date && asOf ? formatDue(item.due_date, asOf) : null;
  const period = borrower?.latest_cycle && borrower.latest_cycle.id === item.cycle_id ? quarterLabel(borrower.latest_cycle.period_end) : null;
  const breach = isBreachItem(item.item_type);

  return (
    <Card data-work-item={item.id} data-item-status={item.status} className={cx('flex flex-col', variant === 'drawer' && 'rounded-none border-0', className)}>
      <div className="px-4 pt-3.5">
        <div className="flex items-center justify-between gap-3 text-caption">
          <SeverityTag severity={item.severity} />
          <span className={cx('tnum', due?.overdue ? 'font-medium text-amber' : 'text-ink-500')}>
            {due ? due.sentence : item.status === 'open' ? 'No due date set' : 'Decided'}
          </span>
        </div>
        <div className="mt-2 text-caption text-ink-500">
          {borrower ? (
            <Link
              to="/borrowers/$code"
              params={{ code: borrower.code }}
              className="font-medium text-ink-700 underline decoration-hairline-strong underline-offset-2 hover:text-cobalt-strong"
            >
              {item.borrower_name}
            </Link>
          ) : (
            <span className="font-medium text-ink-700">{item.borrower_name}</span>
          )}
          {period ? <> · {period}</> : null} · {stageLabel(item.stage)}
        </div>
        <Heading className="mt-1 text-title font-semibold text-pretty text-ink">{item.question}</Heading>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 text-caption text-ink-500">
          {breach ? (
            <StatusDot tone="breach" emphasis>
              {itemTypeLabel(item.item_type)}
            </StatusDot>
          ) : (
            <span>{itemTypeLabel(item.item_type)}</span>
          )}
          <span className="ident">{item.id.slice(0, 8)}</span>
        </div>
        {variant === 'drawer' ? (
          <button
            type="button"
            data-ask-copilot
            onClick={() => drawer.openCopilot({ kind: 'item', itemId: item.id })}
            className="mt-2 inline-flex items-center gap-1.5 text-left text-caption font-medium text-iris hover:underline"
          >
            <AgentMark size={8} />
            Ask Copilot about {item.borrower_name ? `${item.borrower_name}’s ` : 'this '}
            {itemTypeLabel(item.item_type).toLowerCase()}
          </button>
        ) : null}
      </div>

      <div className="mt-3.5 space-y-4 px-4 pb-4">
        <KeyFigures item={item} />
        <Evidence item={item} code={borrower?.code} headingLevel={SubHeading} />
        {item.item_type === 'spread.value_unverified' || item.item_type === 'spread.does_not_foot' ? (
          <HeldFigures item={item} code={borrower?.code} headingLevel={SubHeading} />
        ) : null}
        {item.recommendation ? (
          <Recommendation recommendation={item.recommendation} item={item} headingLevel={SubHeading} code={borrower?.code} />
        ) : item.status === 'open' ? (
          <p className="rounded-md border border-hairline bg-canvas px-3 py-2 text-body text-pretty text-ink-700">
            No agent recommendation is attached. The evidence above was produced by code; the decision is yours.
          </p>
        ) : null}
        {item.status === 'open' ? (
          <RelatedItems items={(item.related_items ?? []).filter((related) => related.id !== item.id && related.status === 'open')} headingLevel={SubHeading} />
        ) : null}
      </div>

      {item.status === 'open' ? <DecisionForm key={item.id} item={item} /> : <RecordedDecision item={item} />}
    </Card>
  );
}
