import { useMutation } from '@tanstack/react-query';
import { createContext, useContext, useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from 'react';
import { ApiError, errorMessage, post } from '@/api/client';
import { useBorrowers, useWorkItem } from '@/api/hooks';
import type { GuardrailNote } from '@/api/types';
import { AgentMark, Button, GuardrailNotes, Quote } from '@/design';
import { Notice, Textarea } from '@/screens/parts';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import { useWorkspaceDrawer } from './context';

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

/**
 * The Copilot: one question, answered by an agent whose figures are stored facts and whose
 * citations code has found on their pages. A refusal is shown as a refusal, never softened.
 */
export function CopilotPanel() {
  const { copilotScope } = useWorkspaceDrawer();
  const [question, setQuestion] = useState('');
  const [exchanges, setExchanges] = useContext(ConversationContext);
  const borrowers = useBorrowers();
  const source = useSource();
  const item = useWorkItem(copilotScope.kind === 'item' ? copilotScope.itemId : null);
  const borrower =
    copilotScope.kind === 'borrower'
      ? borrowers.data?.find((row) => row.code === copilotScope.code)
      : copilotScope.kind === 'item'
        ? borrowers.data?.find((row) => row.id === item.data?.borrower_id)
        : undefined;

  const ask = useMutation({
    mutationFn: (text: string) =>
      post<CopilotReply>('/copilot/ask', {
        question: text,
        borrower_id: borrower?.id ?? null,
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

  return (
    <div data-copilot className="flex h-full flex-col">
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        {exchanges.length === 0 ? (
          <div className="text-body text-pretty text-ink-700">
            <p className="text-title font-semibold text-ink">Ask about {borrower ? 'this borrower' : 'the portfolio'}</p>
            <p className="mt-1">
              The Copilot reads stored facts and documents; it changes nothing. Every figure in an answer is a stored fact that opens its source, and every
              quotation is checked against its page by code. If an answer cannot be grounded, it is refused rather than guessed.
            </p>
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
                <header className="flex items-center justify-between gap-3 px-3.5 pt-2.5">
                  <span className="inline-flex items-center gap-1.5 text-caption font-semibold text-iris">
                    <AgentMark />
                    Copilot
                  </span>
                  <span className="text-caption text-ink-700">
                    {exchange.reply.status === 'answered' ? 'Answered from stored facts' : 'Refused, nothing was guessed'}
                  </span>
                </header>
                <div className="px-3.5 pt-1.5 pb-3">
                  <AgentBody text={exchange.reply.answer_with_references ?? exchange.reply.answer} />
                  {exchange.reply.citations.length > 0 ? (
                    <div className="mt-3">
                      <p className="eyebrow mb-1">Quoted from documents, found on the page by code</p>
                      <ul className="space-y-1.5">
                        {exchange.reply.citations.map((citation, position) => (
                          <li key={position}>
                            {citation.quote ? <Quote text={citation.quote} /> : null}
                            <button
                              type="button"
                              className="link mt-0.5 text-caption font-medium"
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
                              Open page {citation.page}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {exchange.reply.guardrail_notes.length > 0 ? <GuardrailNotes notes={exchange.reply.guardrail_notes} className="mt-3" /> : null}
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
        className="shrink-0 border-t border-hairline-strong px-4 pt-3 pb-4"
      >
        <Textarea
          label={`Your question about ${borrower ? borrower.name : 'the portfolio'}`}
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
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="text-caption text-ink-500">Each question starts an agent run, recorded under Agent activity.</span>
          <Button type="submit" variant="primary" disabled={ask.isPending || !question.trim()}>
            {ask.isPending ? 'Asking' : 'Ask'}
          </Button>
        </div>
      </form>
    </div>
  );
}
