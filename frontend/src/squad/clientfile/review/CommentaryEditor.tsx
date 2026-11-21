import { Plus } from 'lucide-react';
import { useId, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { mul } from '@/api/decimal';
import { useWriteCommentary } from '@/api/hooks';
import type { FactKind, ReviewSheetDetail } from '@/api/schema';
import { Button, fieldLabelClass, formatFigure, Input, Popover, ProvenanceGlyph } from '@/design';
import { humanize } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { Refusal } from '@/repair/FigureForm';
import { AgentBody } from '@/source/AgentBody';

/** The sections a review sheet's commentary is written in, in reading order. */
export const SECTIONS = ['summary', 'performance', 'covenants', 'collateral', 'risks'] as const;

/** Puts a fact reference where the caret is (replacing any selection) and says where the caret goes next. */
export function insertReference(text: string, start: number, end: number, factId: string): { text: string; caret: number } {
  const token = `{{fact:${factId}}}`;
  const from = Math.max(0, Math.min(start, text.length));
  const to = Math.max(from, Math.min(end, text.length));
  return { text: text.slice(0, from) + token + text.slice(to), caret: from + token.length };
}

export interface SheetFigure {
  id: string;
  label: string;
  /** The figure as the workspace shows it. */
  text: string;
  kind: FactKind;
}

/** Every fact on the review sheet, named as the sheet names it, in alphabetical order. */
export function sheetFigures(sheet: Pick<ReviewSheetDetail, 'facts' | 'content'>): SheetFigure[] {
  const labels = sheet.content.fact_labels ?? {};
  return Object.entries(sheet.facts)
    .map(([id, fact]) => ({
      id,
      label: labels[id] ?? humanize(fact.key),
      text: formatFigure(fact.unit === 'pct' ? mul(fact.value, '100') : fact.value, fact.unit).text,
      kind: fact.kind,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Pick a figure from the review sheet instead of typing its reference. Type to narrow the list;
 * Up and Down move, Enter inserts, Escape closes.
 */
function FigurePicker({ figures, onPick }: { figures: SheetFigure[]; onPick: (id: string) => void }) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  // After a figure is picked, focus goes back to the text (the editor moves it), not to the button.
  const picked = useRef(false);
  const matches = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    return figures.filter((figure) => words.every((word) => figure.label.toLowerCase().includes(word)));
  }, [figures, query]);
  const current = Math.min(active, Math.max(matches.length - 1, 0));

  function choose(figure: SheetFigure | undefined) {
    if (!figure) return;
    picked.current = true;
    setOpen(false);
    setQuery('');
    setActive(0);
    onPick(figure.id);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const next = current + (event.key === 'ArrowDown' ? 1 : -1);
      const index = (next + matches.length) % Math.max(matches.length, 1);
      setActive(index);
      document.getElementById(`${listId}-${index}`)?.scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'Enter') {
      event.preventDefault();
      choose(matches[current]);
    }
  }

  return (
    <Popover
      open={open}
      onOpenChange={setOpen}
      label="Figures on this review sheet"
      className="w-[440px]"
      align="end"
      onCloseAutoFocus={(event) => {
        if (picked.current) event.preventDefault();
        picked.current = false;
      }}
      trigger={
        <Button size="sm" iconLeft={<Plus size={13} aria-hidden />} disabled={figures.length === 0}>
          Insert a figure
        </Button>
      }
    >
      <div className="border-b border-hairline p-2">
        <Input
          label="Find a figure on this sheet"
          hideLabel
          placeholder="Find a figure on this sheet"
          role="combobox"
          aria-expanded
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={matches.length > 0 ? `${listId}-${current}` : undefined}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
        />
      </div>
      {matches.length === 0 ? (
        <p className="px-3 py-3 text-body text-ink-500">No figure on this sheet matches. Only stored facts on the sheet can be referred to.</p>
      ) : (
        <ul id={listId} role="listbox" aria-label="Figures on this review sheet" className="max-h-72 overflow-y-auto p-1">
          {matches.map((figure, index) => (
            <li
              key={figure.id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === current}
              tabIndex={-1}
              onClick={() => choose(figure)}
              onKeyDown={(event) => (event.key === 'Enter' ? choose(figure) : undefined)}
              onMouseMove={() => setActive(index)}
              className={cx('flex min-h-8 cursor-pointer items-center justify-between gap-4 rounded-xs px-2 py-1 text-body text-ink select-none', index === current && 'bg-cobalt-bg')}
            >
              <span className="min-w-0 text-pretty">{figure.label}</span>
              <span className="inline-flex shrink-0 items-center gap-1">
                <span className="tnum">{figure.text}</span>
                <ProvenanceGlyph kind={figure.kind} />
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="border-t border-hairline px-3 py-1.5 text-caption text-ink-500">Up and Down move. Enter inserts the figure where the caret was.</p>
    </Popover>
  );
}

export interface CommentaryEditorProps {
  sheet: ReviewSheetDetail;
  section: string;
  /** The version being replaced, or 0 when the section has not been written. */
  version: number;
  initialBody: string;
  /** Called with the server's warnings once the new version is stored. */
  onSaved: (warnings: string[]) => void;
  onCancel: () => void;
}

/**
 * A person writes or edits one section, in place. Figures are not typed: they are picked from the
 * review sheet and stored as references, so the text always shows the stored fact. Saving stores a
 * new draft version; approving it is a separate step, by another person.
 */
export function CommentaryEditor({ sheet, section, version, initialBody, onSaved, onCancel }: CommentaryEditorProps) {
  const write = useWriteCommentary();
  const fieldId = useId();
  const area = useRef<HTMLTextAreaElement>(null);
  // Until the person has put the caret somewhere, a figure goes at the end of the text.
  const placed = useRef(false);
  const [body, setBody] = useState(initialBody);
  const [problem, setProblem] = useState<string | null>(null);
  const figures = useMemo(() => sheetFigures(sheet), [sheet]);
  const name = humanize(section);

  function insert(factId: string) {
    const field = area.current;
    const start = placed.current && field ? field.selectionStart : body.length;
    const end = placed.current && field ? field.selectionEnd : body.length;
    const next = insertReference(body, start, end, factId);
    setBody(next.text);
    setProblem(null);
    // After React has written the new text: back to the field, caret after the reference.
    requestAnimationFrame(() => {
      area.current?.focus();
      area.current?.setSelectionRange(next.caret, next.caret);
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!body.trim()) {
      setProblem('Write the section before saving it.');
      return;
    }
    setProblem(null);
    write.mutate({ sheetId: sheet.id, section, body: body.trim() }, { onSuccess: (saved) => onSaved(saved.warnings ?? []) });
  }

  return (
    <form onSubmit={submit} noValidate aria-label={`Edit ${name.toLowerCase()}`} data-commentary-editor={section} className="rounded-md border border-hairline-strong bg-surface px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label htmlFor={fieldId} className={cx(fieldLabelClass, 'mb-0 text-body font-semibold text-ink')}>
          {name}
          <span className="ml-2 text-caption font-regular text-ink-500">{version > 0 ? `Editing version ${version}; saved as version ${version + 1}, written by you` : 'Not yet written; saved as version 1, written by you'}</span>
        </label>
        <FigurePicker figures={figures} onPick={insert} />
      </div>
      <textarea
        id={fieldId}
        ref={area}
        rows={7}
        value={body}
        aria-invalid={problem ? true : undefined}
        aria-describedby={`${fieldId}-note`}
        onFocus={() => (placed.current = true)}
        onChange={(event) => {
          setBody(event.target.value);
          setProblem(null);
        }}
        className={cx(
          'mt-2 block min-h-[140px] w-full resize-y rounded-sm border bg-surface px-2.5 py-1.5 text-prose text-ink t-colors placeholder:text-ink-500',
          problem ? 'border-amber-mark' : 'border-ink-400 hover:border-ink-500',
        )}
      />
      <p id={`${fieldId}-note`} className={cx('mt-1 text-caption text-pretty', problem ? 'font-medium text-amber' : 'text-ink-500')}>
        {problem ?? 'A figure is stored as a reference to a fact on this sheet and shown from the stored value. A number typed by hand is yours to stand behind; the server warns about each one.'}
      </p>
      {body.trim() ? (
        <div className="mt-3 rounded-sm border border-hairline bg-canvas px-3 py-2" data-commentary-preview>
          <p className="eyebrow mb-1">As it will read</p>
          <AgentBody text={body} />
        </div>
      ) : null}
      {write.error ? <Refusal error={write.error} className="mt-2" /> : null}
      <div className="mt-3 flex items-center gap-2">
        <Button type="submit" variant="primary" size="sm" disabled={write.isPending}>
          {write.isPending ? 'Saving' : 'Save as a draft'}
        </Button>
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={write.isPending}>
          Cancel
        </Button>
        <span className="text-caption text-ink-500">Saving does not approve it: approval stays a separate decision.</span>
      </div>
    </form>
  );
}
