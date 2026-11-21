// frontend/src/squad/shell/commands.ts
import type { Command } from '@/design';
import { LOOK_IDS, LOOKS, type LookId } from '../looks';

export const OVERSIGHT_ROLES = ['admin', 'credit_review', 'credit_admin'];

export interface CommandInput {
  clients: Array<{ code: string; name: string }>;
  go: (path: string) => void;
  setLook: (id: LookId) => void;
  role: string;
  approvals: boolean;
}

export function buildCommands({ clients, go, setLook, role, approvals }: CommandInput): Command[] {
  const commands: Command[] = [
    { id: 'go-squad', group: 'Go to', label: 'Squad', hint: 'The briefing', run: () => go('/') },
    { id: 'go-portfolio', group: 'Go to', label: 'My Portfolio', hint: 'All clients with trend', run: () => go('/portfolio') },
  ];
  if (approvals) commands.push({ id: 'go-approvals', group: 'Go to', label: 'Approvals', hint: 'Decisions waiting for you', run: () => go('/approvals') });
  if (OVERSIGHT_ROLES.includes(role)) {
    commands.push(
      { id: 'go-activity', group: 'Oversight', label: 'Agent activity', run: () => go('/agent-activity') },
      { id: 'go-governance', group: 'Oversight', label: 'Governance and the ledger', run: () => go('/governance') },
    );
  }
  for (const c of clients) commands.push({ id: `client-${c.code}`, group: 'Clients', label: c.name, hint: c.code, searchOnly: true, run: () => go(`/clients/${c.code}`) });
  for (const id of LOOK_IDS) commands.push({ id: `look-${id}`, group: 'Look', label: LOOKS[id].label, hint: 'Change the look', keywords: 'theme colour', run: () => setLook(id) });
  return commands;
}
