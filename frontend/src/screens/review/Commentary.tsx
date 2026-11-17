import { Pencil } from 'lucide-react';
import { useState } from 'react';
import type { CommentaryRow, ReviewSheetDetail } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { AgentNote, Button, Select, StatusDot } from '@/design';
import { humanize, roleLabel, ROLES_WITH } from '@/domain/labels';
import { AgentBody } from '@/source/AgentBody';
import { Notice } from '../parts';
import { CommentaryEditor, SECTIONS } from './CommentaryEditor';

const order = (section: string) => {
  const index = (SECTIONS as readonly string[]).indexOf(section);
  return index === -1 ? SECTIONS.length : index;
};

function Saved({ section, warnings, onDismiss }: { section: string; warnings: string[]; onDismiss: () => void }) {
  return (
    <div data-commentary-saved={section}>
      <Notice
        tone={warnings.length > 0 ? 'attention' : 'neutral'}
        title={warnings.length > 0 ? `${humanize(section)} saved as a draft, with ${warnings.length} ${warnings.length === 1 ? 'warning' : 'warnings'} from the server` : `${humanize(section)} saved as a draft`}
        action={
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
        }
      >
        {warnings.length > 0 ? (
          <ul className="list-disc space-y-0.5 pl-4">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : (
          'The new version is in the ledger. It is a draft until it is approved.'
        )}
      </Notice>
    </div>
  );
}

/**
 * The commentary of a review sheet, section by section. A person with the permission edits a
 * section in place or writes one that is missing; the server's warnings are shown as it gives them.
 * Agent-written text stays marked as the agent's until a person's version replaces it.
 */
export function Commentary({ sheet }: { sheet: ReviewSheetDetail }) {
  const { user, can } = useAuth();
  const [editing, setEditing] = useState<string | null>(null);
  const [saved, setSaved] = useState<Record<string, string[]>>({});
  const [adding, setAdding] = useState('');
  const released = sheet.status === 'released';
  const mayEdit = can('edit_commentary') && !released;
  const sections = [...sheet.commentary].sort((a, b) => order(a.section) - order(b.section) || a.section.localeCompare(b.section));
  const missing = SECTIONS.filter((name) => !sheet.commentary.some((row) => row.section === name));
  const toAdd = missing.includes(adding as (typeof SECTIONS)[number]) ? adding : (missing[0] ?? '');
  const holders = (ROLES_WITH.edit_commentary ?? []).map(roleLabel);

  const done = (section: string) => (warnings: string[]) => {
    setSaved((current) => ({ ...current, [section]: warnings }));
    setEditing(null);
  };
  const dismiss = (section: string) => setSaved((current) => Object.fromEntries(Object.entries(current).filter(([name]) => name !== section)));

  const editButton = (row: CommentaryRow) =>
    mayEdit ? (
      <div className="mt-2">
        <Button size="sm" iconLeft={<Pencil size={12} aria-hidden />} aria-label={`Edit ${humanize(row.section).toLowerCase()}`} onClick={() => setEditing(row.section)}>
          Edit
        </Button>
      </div>
    ) : null;

  return (
    <div className="space-y-4" data-commentary>
      {sections.length === 0 && editing === null ? <p className="text-body text-ink-700">No commentary has been written for this sheet.</p> : null}
      {sections.map((row) => (
        <div key={row.section} className="space-y-2" data-commentary-section={row.section}>
          {editing === row.section ? (
            <CommentaryEditor sheet={sheet} section={row.section} version={row.version} initialBody={row.body} onSaved={done(row.section)} onCancel={() => setEditing(null)} />
          ) : row.written_by_agent ? (
            <AgentNote agent="Review Agent" headline={`${humanize(row.section)}, version ${row.version}`} state={row.status === 'approved' ? 'approved' : 'draft'} approvedBy={sheet.approved_by_name ?? undefined} runId={row.agent_run_id?.slice(0, 8)}>
              <AgentBody text={row.body} />
              {editButton(row)}
            </AgentNote>
          ) : (
            <section aria-label={`${humanize(row.section)}, written by ${row.author_name ?? 'a person'}`} className="rounded-md border border-hairline-strong px-4 py-3">
              <div className="flex items-center justify-between gap-3 text-caption">
                <span className="font-semibold text-ink">
                  {humanize(row.section)}, version {row.version} · {row.author_name ?? 'A person'}
                </span>
                <StatusDot tone={row.status === 'approved' ? 'pass' : 'attention'}>{row.status === 'approved' ? 'Approved' : 'Draft, not yet approved'}</StatusDot>
              </div>
              <AgentBody text={row.body} className="mt-1.5" />
              {editButton(row)}
            </section>
          )}
          {saved[row.section] ? <Saved section={row.section} warnings={saved[row.section] ?? []} onDismiss={() => dismiss(row.section)} /> : null}
        </div>
      ))}
      {editing !== null && !sections.some((row) => row.section === editing) ? (
        <CommentaryEditor sheet={sheet} section={editing} version={0} initialBody="" onSaved={done(editing)} onCancel={() => setEditing(null)} />
      ) : null}
      {mayEdit && missing.length > 0 && editing === null ? (
        <div className="flex flex-wrap items-end gap-2 border-t border-hairline pt-3">
          <Select label="Section not yet written" className="w-64" value={toAdd} onValueChange={setAdding} options={missing.map((name) => ({ value: name, label: humanize(name) }))} />
          <Button onClick={() => setEditing(toAdd)}>Write this section</Button>
        </div>
      ) : null}
      {released ? <p className="text-caption text-ink-500">This review sheet is released: its commentary can no longer be edited.</p> : null}
      {!released && !can('edit_commentary') && user ? (
        <p className="text-caption text-ink-500">
          Writing commentary needs {holders.length > 0 ? `a ${holders.join(' or a ').toLowerCase()}` : 'another role'}. Your role, {roleLabel(user.role)}, can read it.
        </p>
      ) : null}
    </div>
  );
}
