import { Link } from '@tanstack/react-router';
import { errorMessage } from '@/api/client';
import { useAgentsStatus, useRunCycle } from '@/api/hooks';
import type { BorrowerOverview } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { Button } from '@/design';
import { stageLabel, stageStatusLabel } from '@/domain/labels';
import { Notice } from '@/screens/parts';

type Cycle = NonNullable<BorrowerOverview['cycle']>;

/**
 * Lets a person who may run agents move the cycle one stage, now. The stage calls its agent and
 * its code checks in the request; what it did is then listed under Agent activity. Where no model
 * is connected the button is off and says why, so a stage is never failed by pressing it.
 */
export function RunStage({ cycle, code }: { cycle: Cycle; code?: string }) {
  const { can } = useAuth();
  const status = useAgentsStatus();
  const run = useRunCycle(cycle.id);
  if (!can('run_agents') || cycle.status === 'closed') return null;

  const current = cycle.stages.find((stage) => stage.stage === cycle.stage);
  const next = cycle.stages.find((stage) => stage.status === 'pending' || stage.status === 'running');
  const waitingForPerson = current?.status === 'needs_person' || current?.status === 'failed';
  const label = next ? stageLabel(next.stage) : null;
  const connected = status.data?.model_connected ?? false;
  const result = run.data;

  return (
    <div data-run-stage className="mt-3 border-t border-hairline pt-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Button variant="primary" size="sm" disabled={!connected || !label || waitingForPerson || run.isPending} onClick={() => run.mutate()}>
          {run.isPending ? `Running ${label ?? 'the stage'}` : label ? `Run ${label} now` : 'Nothing to run'}
        </Button>
        <p className="min-w-0 flex-1 text-caption text-pretty text-ink-700">
          {run.isPending
            ? 'The agent is reading and code is checking its answer. This can take a minute or two; stay on this page.'
            : waitingForPerson
              ? `${stageLabel(cycle.stage)} is waiting for a person. The next stage can run once its open items are decided.`
              : !status.data
                ? 'Checking whether a model is connected.'
                : !connected
                  ? `Agents cannot run here. ${status.data.reason}`
                  : `Runs one stage with its agent (model ${status.data.model}) and stops. Each run is billable and is recorded in the ledger in your name.`}
        </p>
      </div>
      {run.error ? (
        <Notice tone="attention" title="The stage was not run" className="mt-3">
          The server said: “{errorMessage(run.error)}”
        </Notice>
      ) : null}
      {result && !run.isPending ? (
        <Notice
          tone={result.ran.some((entry) => entry.result === 'failed') ? 'attention' : 'neutral'}
          title={result.ran.length > 0 ? 'What ran' : 'Nothing ran'}
          className="mt-3"
        >
          {result.ran.length > 0 ? (
            <ul className="space-y-0.5">
              {result.ran.map((entry) => (
                <li key={entry.stage}>
                  <span className="font-medium text-ink">{stageLabel(entry.stage)}</span>:{' '}
                  {entry.result ? stageStatusLabel(entry.result) : 'Not run'}
                  {entry.error ? `. ${entry.error}` : ''}
                </li>
              ))}
            </ul>
          ) : (
            <p>No stage was ready to run.</p>
          )}
          <p className="mt-1">
            {result.open_blocking_items > 0
              ? `${result.open_blocking_items} open ${result.open_blocking_items === 1 ? 'item needs' : 'items need'} a person before the cycle moves on. `
              : ''}
            {code ? (
              <Link to="/clients/$code/file/$view" params={{ code, view: 'runs' }} className="link font-medium">
                See what the agents did
              </Link>
            ) : null}
          </p>
        </Notice>
      ) : null}
    </div>
  );
}
