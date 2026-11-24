// frontend/src/squad/shell/commands.ts
import type { Command } from '@/design';
import { LOOK_IDS, LOOKS, type LookId } from '../looks';

export interface CommandInput {
  clients: Array<{ code: string; name: string }>;
  go: (path: string) => void;
  setLook: (id: LookId) => void;
  /** Whether the server offers this person Oversight (`briefing.oversight.offered`); the browser keeps no list of roles. */
  oversight: boolean;
  approvals: boolean;
}

export function buildCommands({ clients, go, setLook, oversight, approvals }: CommandInput): Command[] {
  const commands: Command[] = [
    { id: 'go-squad', group: 'Go to', label: 'Squad', hint: 'The briefing', run: () => go('/') },
    { id: 'go-portfolio', group: 'Go to', label: 'My Portfolio', hint: 'All clients with trend', run: () => go('/portfolio') },
  ];
  commands.push({ id: 'go-review-room', group: 'Go to', label: 'Review room', hint: 'Meetings, sheets, commentary and actions', run: () => go('/review-room') });
  if (approvals) commands.push({ id: 'go-approvals', group: 'Go to', label: 'Approvals', hint: 'Decisions waiting for you', run: () => go('/approvals') });
  if (oversight) {
    commands.push(
      { id: 'go-oversight', group: 'Oversight', label: 'Oversight', hint: 'Agent activity, governance, evaluations', run: () => go('/oversight') },
      { id: 'go-ledger', group: 'Oversight', label: 'The ledger', run: () => go('/oversight/ledger') },
    );
  }
  for (const c of clients) commands.push({ id: `client-${c.code}`, group: 'Clients', label: c.name, hint: c.code, searchOnly: true, run: () => go(`/clients/${c.code}`) });
  for (const id of LOOK_IDS) commands.push({ id: `look-${id}`, group: 'Look', label: LOOKS[id].label, hint: 'Change the look', keywords: 'theme colour', run: () => setLook(id) });
  return commands;
}
