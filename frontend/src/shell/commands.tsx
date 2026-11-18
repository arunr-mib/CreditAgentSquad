import { useNavigate } from '@tanstack/react-router';
import { Building2, ListFilter, Palette, Sparkles } from 'lucide-react';
import { useMemo } from 'react';
import { useBorrowers, usePortfolio } from '@/api/hooks';
import type { Severity } from '@/api/types';
import { useAuth } from '@/auth/context';
import type { Command } from '@/design';
import { ITEM_GROUP_LABEL, itemGroup, roleLabel, SEVERITY_LABEL, type ItemGroup } from '@/domain/labels';
import { useWorkspaceDrawer } from '@/drawer/context';
import { NAV } from './nav';

/** The borrower whose page is open, from the address. */
export function borrowerCodeIn(pathname: string): string | undefined {
  return pathname.match(/^\/borrowers\/([^/]+)/)?.[1];
}

const open = (count: number) => `${count} open`;

/**
 * Everything the command palette offers, in four groups: ask the Copilot, filter the exception
 * queue, go to a screen, jump to a borrower. Every count is one the API reported.
 */
export function useShellCommands(pathname: string): Command[] {
  const navigate = useNavigate();
  const borrowers = useBorrowers();
  const portfolio = usePortfolio();
  const { user } = useAuth();
  const { open: drawerOpen, tab, itemId, borrowerCode: tearSheetCode, openCopilot } = useWorkspaceDrawer();
  const code = borrowerCodeIn(pathname);
  const itemInDrawer = drawerOpen && tab === 'item' && !tearSheetCode ? itemId : null;
  const role = user?.role;

  return useMemo<Command[]>(() => {
    const spark = <Sparkles size={15} strokeWidth={1.75} className="text-iris-mark" />;
    const filter = <ListFilter size={15} strokeWidth={1.75} />;
    const borrowerOnScreen = code ? borrowers.data?.find((row) => row.code === code) : undefined;
    const workItems = portfolio.data?.work_items;
    const severityCount = (level: Severity) => workItems?.by_severity.find((entry) => entry.severity === level)?.count;
    /** The queue reads its filters from the address: `severity`, and `type` (a kind of exception, or `mine`). */
    const queue = (search: { severity?: string; type?: string }) => () => void navigate({ to: '/command-centre', search });

    const byGroup = new Map<ItemGroup, number>();
    for (const entry of workItems?.by_type ?? []) byGroup.set(itemGroup(entry.item_type), (byGroup.get(itemGroup(entry.item_type)) ?? 0) + entry.count);

    return [
      ...(borrowerOnScreen
        ? [
            {
              id: 'copilot-borrower',
              group: 'Copilot',
              label: `Ask Copilot about ${borrowerOnScreen.name}`,
              hint: 'The borrower on screen',
              icon: spark,
              keywords: 'question chat agent',
              run: () => openCopilot({ kind: 'borrower', code: borrowerOnScreen.code }),
            },
          ]
        : []),
      ...(itemInDrawer
        ? [
            {
              id: 'copilot-item',
              group: 'Copilot',
              label: 'Ask Copilot about the exception in the drawer',
              hint: 'The selected exception',
              icon: spark,
              keywords: 'question chat agent item',
              run: () => openCopilot({ kind: 'item', itemId: itemInDrawer }),
            },
          ]
        : []),
      {
        id: 'copilot-portfolio',
        group: 'Copilot',
        label: 'Ask Copilot about the portfolio',
        hint: 'Read-only; answers cite stored facts',
        icon: spark,
        keywords: 'question chat agent book',
        run: () => openCopilot({ kind: 'portfolio' }),
      },

      {
        id: 'queue-critical',
        group: 'Queue',
        label: 'Show critical exceptions',
        hint: severityCount('critical') !== undefined ? open(severityCount('critical') ?? 0) : undefined,
        icon: filter,
        keywords: 'filter severity breach',
        run: queue({ severity: 'critical' }),
      },
      {
        id: 'queue-mine',
        group: 'Queue',
        label: 'Show exceptions my role can decide',
        hint: role ? roleLabel(role) : undefined,
        icon: filter,
        keywords: 'filter authority mine sign-off',
        run: queue({ type: 'mine' }),
      },
      {
        id: 'queue-all',
        group: 'Queue',
        label: 'Show every open exception',
        hint: workItems ? open(workItems.open) : undefined,
        icon: filter,
        keywords: 'filter clear all',
        run: queue({}),
      },
      ...(['high', 'medium', 'low'] as const).map((level) => ({
        id: `queue-${level}`,
        group: 'Queue',
        label: `Show ${SEVERITY_LABEL[level].toLowerCase()}-severity exceptions`,
        hint: severityCount(level) !== undefined ? open(severityCount(level) ?? 0) : undefined,
        icon: filter,
        keywords: 'filter',
        searchOnly: true,
        run: queue({ severity: level }),
      })),
      ...[...byGroup.entries()].map(([group, count]) => ({
        id: `queue-type-${group}`,
        group: 'Queue',
        label: `Show ${ITEM_GROUP_LABEL[group].toLowerCase()} exceptions`,
        hint: open(count),
        icon: filter,
        keywords: 'filter type',
        searchOnly: true,
        run: queue({ type: group }),
      })),

      ...NAV.map((item) => ({
        id: `nav-${item.to}`,
        group: 'Go to',
        label: item.label,
        hint: item.description,
        icon: <item.icon size={15} strokeWidth={1.75} />,
        run: () => void navigate({ to: item.to }),
      })),
      {
        id: 'nav-design',
        group: 'Go to',
        label: 'Design system',
        hint: 'Tokens and components',
        icon: <Palette size={15} strokeWidth={1.75} />,
        run: () => void navigate({ to: '/design' }),
      },

      ...(borrowers.data ?? []).map((borrower) => ({
        id: `borrower-${borrower.id}`,
        group: 'Borrowers',
        label: borrower.name,
        hint: borrower.industry,
        icon: <Building2 size={15} strokeWidth={1.75} />,
        keywords: `${borrower.code} ${borrower.analyst ?? ''} ${borrower.relationship_manager ?? ''}`,
        run: () => void navigate({ to: '/borrowers/$code', params: { code: borrower.code } }),
      })),
    ];
  }, [navigate, borrowers.data, portfolio.data, role, code, itemInDrawer, openCopilot]);
}
