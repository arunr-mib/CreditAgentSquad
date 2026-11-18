import { AgentMark, Drawer, EmptyState } from '@/design';
import { cx } from '@/lib/cx';
import { WorkItemPanel } from '@/screens/work/WorkItemPanel';
import { BorrowerTearSheet } from './BorrowerTearSheet';
import { CopilotPanel } from './CopilotPanel';
import { useWorkspaceDrawer, type DrawerTab } from './context';

function TabButton({
  tab,
  current,
  onSelect,
  children,
}: {
  tab: DrawerTab;
  current: DrawerTab;
  onSelect: (tab: DrawerTab) => void;
  children: React.ReactNode;
}) {
  const selected = tab === current;
  return (
    <button
      type="button"
      role="tab"
      id={`drawer-tab-${tab}`}
      aria-selected={selected}
      aria-controls={`drawer-panel-${tab}`}
      tabIndex={selected ? 0 : -1}
      onClick={() => onSelect(tab)}
      className={cx(
        'inline-flex h-7 items-center gap-1.5 rounded-sm px-2.5 text-body font-medium t-colors',
        selected ? 'bg-ink text-canvas' : 'text-ink-700 hover:bg-hover hover:text-ink',
      )}
    >
      {children}
    </button>
  );
}

/**
 * The one drawer of the workspace. Two tabs: the selected exception with its evidence and
 * decision, and the Copilot. Both stay mounted while the drawer is open, so a half-written
 * reason or question survives a switch.
 */
export function WorkspaceDrawer() {
  const drawer = useWorkspaceDrawer();
  return (
    <Drawer
      open={drawer.open}
      onOpenChange={(open) => {
        if (!open) drawer.close();
      }}
      title="the workspace drawer"
      header={
        <div role="tablist" aria-label="Drawer" className="inline-flex items-center gap-1 rounded-sm border border-hairline-strong bg-surface p-0.5">
          <TabButton tab="item" current={drawer.tab} onSelect={drawer.setTab}>
            {drawer.borrowerCode ? 'Borrower' : <>Exception &amp; decision</>}
          </TabButton>
          <TabButton tab="copilot" current={drawer.tab} onSelect={drawer.setTab}>
            <AgentMark size={8} />
            Copilot
          </TabButton>
        </div>
      }
    >
      <div role="tabpanel" id="drawer-panel-item" aria-labelledby="drawer-tab-item" hidden={drawer.tab !== 'item'}>
        {drawer.borrowerCode ? (
          <BorrowerTearSheet key={drawer.borrowerCode} code={drawer.borrowerCode} />
        ) : drawer.itemId ? (
          <WorkItemPanel key={drawer.itemId} itemId={drawer.itemId} variant="drawer" />
        ) : (
          <div className="px-4 py-10">
            <EmptyState title="No exception selected" description="Choose a row in the exception queue to see its evidence and decision here." />
          </div>
        )}
      </div>
      <div
        role="tabpanel"
        id="drawer-panel-copilot"
        aria-labelledby="drawer-tab-copilot"
        hidden={drawer.tab !== 'copilot'}
        className={drawer.tab === 'copilot' ? 'h-full' : undefined}
      >
        <CopilotPanel />
      </div>
    </Drawer>
  );
}
