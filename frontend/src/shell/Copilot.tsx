import { useRouterState } from '@tanstack/react-router';
import { Sparkles } from 'lucide-react';
import { Kbd } from '@/design';
import { useWorkspaceDrawer } from '@/drawer/context';

/** Opens the Copilot in the workspace drawer, scoped to the borrower on screen when there is one. */
export function Copilot() {
  const drawer = useWorkspaceDrawer();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const code = pathname.match(/^\/borrowers\/([^/]+)/)?.[1];
  return (
    <button
      type="button"
      title="Ask a question about a borrower or the portfolio. Answers cite stored facts and documents; nothing is changed. The log of what agents did is under Agent activity."
      aria-keyshortcuts="Control+J Meta+J"
      onClick={() => drawer.openCopilot(code ? { kind: 'borrower', code } : { kind: 'portfolio' })}
      className="inline-flex h-8 shrink-0 items-center gap-2 rounded-sm border border-hairline-strong bg-surface px-2.5 text-body font-medium text-ink t-colors hover:border-ink-400 @max-[520px]:w-8 @max-[520px]:justify-center @max-[520px]:px-0"
    >
      <Sparkles size={15} strokeWidth={1.75} aria-hidden className="shrink-0 text-iris-mark" />
      <span className="whitespace-nowrap @max-[520px]:sr-only">Ask Copilot</span>
      <span aria-hidden className="@max-[940px]:hidden">
        <Kbd>Ctrl J</Kbd>
      </span>
    </button>
  );
}
