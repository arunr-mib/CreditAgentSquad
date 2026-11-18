import { useMutation } from '@tanstack/react-query';
import { Link, useRouterState } from '@tanstack/react-router';
import { BadgeCheck, ClipboardCopy } from 'lucide-react';
import { createContext, useContext, useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from 'react';
import { ApiError, errorMessage, post } from '@/api/client';
import { useAgentsStatus, useBorrowers, usePortfolio, useWorkItem, useWorkItems } from '@/api/hooks';
import type { GuardrailNote } from '@/api/types';
import { useAuth } from '@/auth/context';
import { AgentMark, Button, GuardrailNotes, Kbd, Quote, Select } from '@/design';
import { itemTypeLabel, OUTCOME, roleLabel } from '@/domain/labels';
import { Notice, Textarea } from '@/screens/parts';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import { useWorkspaceDrawer, type CopilotScope } from './context';

interface CopilotCitation {
  document_id: string;
  page: number;
  quote?: string | null;
  document_title?: string | null;
  title?: string | null;
}

interface CopilotReply {
  status: 'answered' | 'refused' | string;
  answer: string;
  answer_with_references?: string;
  fact_ids: string[];
  citations: CopilotCitation[];
  follow_ups: string[];
  guardrail_notes: GuardrailNote[];
  agent_run_id?: string | null;
}

export interface Exchange {
  question: string;
  reply?: CopilotReply;
  error?: string;
  status?: number;
}

type Conversation = [Exchange[], Dispatch<SetStateAction<Exchange[]>>];
const ConversationContext = createContext<Conversation>([[], () => {}]);

/** Keeps the Copilot conversation while the drawer is closed or showing its other tab. */
export function CopilotConversationProvider({ children }: { children: ReactNode }) {
  const state = useState<Exchange[]>([]);
  return <ConversationContext.Provider value={state}>{children}</ConversationContext.Provider>;
}

const scopeKey = (scope: CopilotScope): string =>
  scope.kind === 'portfolio' ? 'portfolio' : scope.kind === 'borrower' ? `borrower:${scope.code}` : `item:${scope.itemId}`;

/**
 * The Copilot: one question, answered by an agent whose figures are stored facts and whose
 * citations code has found on their pages. A refusal is shown as a refusal, never softened.
 * It reads; it changes nothing. What it is asked about (the scope) is chosen here and injected by
 * the server, never by the model.
 */
export function CopilotPanel() {
  const drawer = useWorkspaceDrawer();
  const { copilotScope: scope, setCopilotScope, itemId: openItemId } = drawer;
  const { user } = useAuth();
  const [question, setQuestion] = useState('');
  const [exchanges, setExchanges] = useContext(ConversationContext);
  const borrowers = useBorrowers();
  const portfolio = usePortfolio();
  const queue = useWorkItems({ status: 'open' });
  const status = useAgentsStatus();
  const source = useSource();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const routeCode = pathname.match(/^\/borrowers\/([^/]+)/)?.[1];
  const scopedItem = useWorkItem(scope.kind === 'item' ? scope.itemId : null);
  const openItem = useWorkItem(openItemId);

  const borrower =
    scope.kind === 'borrower'
      ? borrowers.data?.find((row) => row.code === scope.code)
      : scope.kind === 'item'
        ? borrowers.data?.find((row) => row.id === scopedItem.data?.borrower_id)
        : undefined;
  const subject =
    scope.kind === 'item' && scopedItem.data
      ? `${scopedItem.data.borrower_name ?? 'the borrower'}’s ${itemTypeLabel(scopedItem.data.item_type).toLowerCase()}`
      : borrower
        ? borrower.name
        : 'the portfolio';
  const connected = status.data?.model_connected ?? false;

  /* ── Scope ── */
  const routeBorrower = routeCode ? borrowers.data?.find((row) => row.code === routeCode) : undefined;
  const options: Array<{ value: string; label: string; scope: CopilotScope }> = [
    { value: 'portfolio', label: `Whole portfolio${portfolio.data ? ` (${portfolio.data.borrowers} borrowers)` : ''}`, scope: { kind: 'portfolio' } },
  ];
  for (const candidate of [borrower, routeBorrower]) {
    if (candidate && !options.some((option) => option.value === `borrower:${candidate.code}`)) {
      options.push({ value: `borrower:${candidate.code}`, label: candidate.name, scope: { kind: 'borrower', code: candidate.code } });
    }
  }
  for (const item of [scopedItem.data, openItem.data]) {
    if (item && item.status === 'open' && !options.some((option) => option.value === `item:${item.id}`)) {
      options.push({
        value: `item:${item.id}`,
        label: `Selected exception: ${item.borrower_name ?? 'borrower'} · ${item.id.slice(0, 8)}`,
        scope: { kind: 'item', itemId: item.id },
      });
    }
  }

  /* ── Asking ── */
  const ask = useMutation({
    mutationFn: (text: string) =>
      post<CopilotReply>('/copilot/ask', {
        question: text,
        borrower_id: borrower?.id ?? null,
        work_item_id: scope.kind === 'item' ? scope.itemId : null,
        history: exchanges
          .filter((exchange) => exchange.reply?.status === 'answered')
          .flatMap((exchange) => [
            { role: 'user', text: exchange.question },
            { role: 'assistant', text: exchange.reply?.answer ?? '' },
          ])
          .slice(-10),
      }),
  });

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || ask.isPending) return;
    setQuestion('');
    setExchanges((list) => [...list, { question: trimmed }]);
    ask.mutate(trimmed, {
      onSuccess: (reply) => setExchanges((list) => list.map((exchange, index) => (index === list.length - 1 ? { ...exchange, reply } : exchange))),
      onError: (error) =>
        setExchanges((list) =>
          list.map((exchange, index) =>
            index === list.length - 1 ? { ...exchange, error: errorMessage(error), status: error instanceof ApiError ? error.status : 0 } : exchange,
          ),
        ),
    });
  }

  /* ── Starters: built from what is on file now, never typed into the source ── */
  const items = queue.data ?? [];
  const mismatches = portfolio.data?.covenants.by_outcome.find((entry) => entry.outcome === 'breach_reported_compliant')?.count ?? 0;
  const focus = scopedItem.data ?? openItem.data ?? items[0];
  const starters: string[] = [];
  if (mismatches > 0)
    starters.push(
      `Audit the ${mismatches} covenant ${mismatches === 1 ? 'test' : 'tests'} marked “${OUTCOME.breach_reported_compliant.label}” and show the gap between the calculated and reported ratios.`,
    );
  if (user && items.length > 0) starters.push(`Which of the ${items.length} open exceptions can ${user.name} (${roleLabel(user.role)}) decide right now?`);
  if (focus)
    starters.push(
      `Summarise ${focus.borrower_name ?? 'the borrower'}’s ${itemTypeLabel(focus.item_type).toLowerCase()} (${focus.id.slice(0, 8)}) and the evidence behind it.`,
    );
  starters.push('List the overdue deliverables and any missing financial statement pages.');

  return (
    <div data-copilot className="flex h-full flex-col">
      <div className="shrink-0 border-b border-hairline px-4 py-2.5">
        <Select
          label="Scope"
          className="w-full"
          value={scopeKey(scope)}
          onValueChange={(value) => setCopilotScope(options.find((option) => option.value === value)?.scope ?? { kind: 'portfolio' })}
          options={options.map(({ value, label }) => ({ value, label }))}
        />
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        {exchanges.length === 0 ? (
          <div data-copilot-empty>
            <p className="inline-flex items-center gap-1.5 text-title font-semibold text-ink">
              <AgentMark />
              Ask about {subject}
            </p>
            <p className="mt-1 text-body text-pretty text-ink-700">
              Every figure in an answer is a stored fact that opens its source, and every quotation is checked against its page by code. An answer that cannot
              be grounded is refused, not guessed.
            </p>
            {status.data && !connected ? (
              <Notice tone="attention" title="The Copilot cannot answer here" className="mt-3">
                {status.data.reason}
              </Notice>
            ) : null}
            <p className="eyebrow mt-4 mb-1.5">Start with</p>
            <ul className="grid gap-2">
              {starters.map((starter) => (
                <li key={starter}>
                  <button
                    type="button"
                    data-starter
                    disabled={!connected || ask.isPending}
                    onClick={() => send(starter)}
                    className="w-full rounded-md border border-hairline-strong bg-surface px-3 py-2.5 text-left text-body text-pretty text-ink t-colors hover:border-iris-border hover:bg-iris-bg disabled:text-ink-500 disabled:hover:border-hairline-strong disabled:hover:bg-surface"
                  >
                    {starter}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {exchanges.map((exchange, index) => (
          <div key={index} className="space-y-2">
            <p className="rounded-md border border-hairline bg-canvas px-3 py-2 text-body text-ink">
              <span className="eyebrow mb-0.5 block">You asked</span>
              {exchange.question}
            </p>
            {exchange.error ? (
              <Notice tone="attention" title={exchange.status === 503 ? 'The Copilot’s model is not available' : 'The Copilot could not answer'}>
                The server said: “{exchange.error}”
              </Notice>
            ) : !exchange.reply ? (
              <p role="status" className="inline-flex items-center gap-1.5 text-body text-iris">
                <AgentMark size={8} /> Reading the facts and documents
              </p>
            ) : (
              <section
                aria-label={`Written by the Copilot: ${exchange.reply.status}`}
                data-copilot-status={exchange.reply.status}
                className="rounded-md border border-iris-border bg-iris-bg"
              >
                <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-3.5 pt-2.5">
                  <span className="inline-flex items-center gap-1.5 text-caption font-semibold text-iris">
                    <AgentMark />
                    Copilot
                  </span>
                  <span className="text-caption text-ink-700">
                    {exchange.reply.status === 'answered' ? 'Answered from stored facts' : 'Refused, nothing was guessed'}
                  </span>
                </header>
                <div className="px-3.5 pt-1.5 pb-3">
                  <AgentBody text={exchange.reply.answer_with_references ?? exchange.reply.answer} chips />
                  {exchange.reply.citations.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {exchange.reply.citations.map((citation, position) => (
                        <li key={position}>
                          {citation.quote ? <Quote text={citation.quote} /> : null}
                          <button
                            type="button"
                            data-verified-quote
                            className="mt-1 inline-flex items-center gap-1 rounded-full border border-green-border bg-green-bg px-2 py-0.5 text-caption font-medium text-green t-colors hover:border-green"
                            onClick={() =>
                              source.open({
                                type: 'document',
                                documentId: citation.document_id,
                                page: citation.page,
                                quote: citation.quote,
                                title: citation.document_title ?? citation.title ?? 'Document',
                                borrowerCode: borrower?.code,
                              })
                            }
                          >
                            <BadgeCheck size={12} aria-hidden />
                            Quote verified by code · p. {citation.page}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {exchange.reply.guardrail_notes.length > 0 ? <GuardrailNotes notes={exchange.reply.guardrail_notes} className="mt-3" /> : null}
                  <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
                    {exchange.reply.status === 'answered' && openItem.data?.status === 'open' ? (
                      <Button
                        size="sm"
                        data-copy-reason
                        onClick={() => {
                          const run = exchange.reply?.agent_run_id
                            ? ` (from the Copilot, run ${exchange.reply.agent_run_id.slice(0, 8)})`
                            : ' (from the Copilot)';
                          if (openItem.data) drawer.draftReason(openItem.data.id, `${exchange.reply?.answer ?? ''}${run}`);
                        }}
                      >
                        <ClipboardCopy size={13} aria-hidden />
                        Copy to decision reason
                      </Button>
                    ) : null}
                    {exchange.reply.agent_run_id ? (
                      <Link to="/agent-activity" search={{ run: exchange.reply.agent_run_id }} className="link text-caption font-medium">
                        See this run, step by step
                      </Link>
                    ) : null}
                  </div>
                  {exchange.reply.follow_ups.length > 0 ? (
                    <div className="mt-3">
                      <p className="eyebrow mb-1">You could ask next</p>
                      <ul className="space-y-1">
                        {exchange.reply.follow_ups.map((follow) => (
                          <li key={follow}>
                            <button type="button" className="link text-left text-body" onClick={() => send(follow)}>
                              {follow}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </section>
            )}
          </div>
        ))}
      </div>

      <form
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          send(question);
        }}
        className="shrink-0 border-t border-hairline-strong px-4 pt-3 pb-3"
      >
        <Textarea
          label={`Your question about ${subject}`}
          rows={2}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              send(question);
            }
          }}
          placeholder={borrower ? 'Why did leverage rise this quarter?' : 'Which borrowers are in breach?'}
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <span className="inline-flex flex-wrap items-center gap-1 text-caption text-ink-700">
            <Kbd>Enter</Kbd> to send, <Kbd>Shift</Kbd>
            <Kbd>Enter</Kbd> for a new line.
          </span>
          <Button type="submit" variant="primary" disabled={ask.isPending || !question.trim() || (status.data ? !connected : false)}>
            {ask.isPending ? 'Asking' : 'Ask'}
          </Button>
        </div>
        <p className="mt-2 text-caption text-pretty text-ink-500">
          Read-only. Grounded in verified filings and stored facts; unverifiable claims are refused. Each question starts a billable agent run, listed under{' '}
          <Link to="/agent-activity" className="link">
            Agent activity
          </Link>
          .
        </p>
      </form>
    </div>
  );
}
