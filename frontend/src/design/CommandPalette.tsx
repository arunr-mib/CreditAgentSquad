import { CornerDownLeft, Search } from 'lucide-react';
import { Dialog as RadixDialog } from 'radix-ui';
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { cx } from '@/lib/cx';
import { overlayClass } from './Dialog';
import { Kbd } from './Kbd';

export interface Command {
  id: string;
  group: string;
  label: string;
  /** Secondary text on the right: a borrower id, a shortcut, a section. */
  hint?: string;
  icon?: ReactNode;
  keywords?: string;
  run: () => void;
}

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: Command[];
  placeholder?: string;
}

/** Opens the palette on Ctrl-K or Cmd-K from anywhere. */
export function useCommandPaletteShortcut(onToggle: () => void) {
  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        onToggle();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onToggle]);
}

export function CommandPalette({ open, onOpenChange, commands, placeholder = 'Search borrowers and commands' }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const listId = useId();
  const listRef = useRef<HTMLDivElement>(null);

  const matches = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (words.length === 0) return commands;
    return commands.filter((command) => {
      const haystack = `${command.label} ${command.group} ${command.hint ?? ''} ${command.keywords ?? ''}`.toLowerCase();
      return words.every((word) => haystack.includes(word));
    });
  }, [commands, query]);

  const groups = useMemo(() => {
    const map = new Map<string, Array<{ command: Command; index: number }>>();
    matches.forEach((command, index) => {
      const bucket = map.get(command.group) ?? [];
      bucket.push({ command, index });
      map.set(command.group, bucket);
    });
    return [...map.entries()];
  }, [matches]);

  const activeIndex = Math.min(active, Math.max(matches.length - 1, 0));

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  function handleOpenChange(next: boolean) {
    if (next) {
      setQuery('');
      setActive(0);
    }
    onOpenChange(next);
  }

  function run(command: Command | undefined) {
    if (!command) return;
    handleOpenChange(false);
    command.run();
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive(matches.length === 0 ? 0 : (activeIndex + 1) % matches.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive(matches.length === 0 ? 0 : (activeIndex - 1 + matches.length) % matches.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      run(matches[activeIndex]);
    }
  }

  return (
    <RadixDialog.Root open={open} onOpenChange={handleOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className={overlayClass} />
        <RadixDialog.Content
          aria-describedby={undefined}
          className="anim-rise fixed top-[14vh] left-1/2 z-50 w-[600px] -translate-x-1/2 overflow-hidden rounded-md border border-hairline-strong bg-surface shadow-overlay"
        >
          <RadixDialog.Title className="sr-only">Command palette</RadixDialog.Title>
          <div className="flex h-12 items-center gap-3 border-b border-hairline-strong px-4">
            <Search size={16} aria-hidden className="shrink-0 text-ink-500" />
            <input
              role="combobox"
              aria-label="Search"
              aria-expanded
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={matches[activeIndex] ? `${listId}-${matches[activeIndex].id}` : undefined}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActive(0);
              }}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              className="h-full min-w-0 flex-1 bg-transparent text-prose text-ink outline-none placeholder:text-ink-500"
            />
            <Kbd>Esc</Kbd>
          </div>
          <div ref={listRef} id={listId} role="listbox" aria-label="Results" className="max-h-[360px] overflow-y-auto p-1.5">
            {matches.length === 0 ? (
              <p className="px-3 py-6 text-body text-ink-700">Nothing matches “{query}”. Try a borrower name or a section.</p>
            ) : (
              groups.map(([group, entries]) => (
                <div key={group} role="group" aria-label={group} className="mb-1 last:mb-0">
                  <div className="eyebrow px-2.5 pt-2 pb-1">{group}</div>
                  {entries.map(({ command, index }) => {
                    const selected = index === activeIndex;
                    return (
                      <div
                        key={command.id}
                        id={`${listId}-${command.id}`}
                        role="option"
                        tabIndex={-1}
                        aria-selected={selected}
                        onMouseMove={() => setActive(index)}
                        onClick={() => run(command)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') run(command);
                        }}
                        className={cx('flex h-9 cursor-pointer items-center gap-2.5 rounded-sm px-2.5 text-body text-ink', selected && 'bg-cobalt-bg')}
                      >
                        {command.icon ? <span className={cx('flex shrink-0', selected ? 'text-cobalt-strong' : 'text-ink-500')}>{command.icon}</span> : null}
                        <span className="min-w-0 flex-1 font-medium text-pretty">{command.label}</span>
                        {command.hint ? <span className="shrink-0 text-caption text-ink-500">{command.hint}</span> : null}
                        {selected ? <CornerDownLeft size={12} aria-hidden className="shrink-0 text-cobalt-strong" /> : null}
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>
          <div className="flex items-center gap-4 border-t border-hairline px-4 py-2 text-caption text-ink-500">
            <span className="inline-flex items-center gap-1.5">
              <Kbd>↑</Kbd>
              <Kbd>↓</Kbd> to move
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Kbd>Enter</Kbd> to open
            </span>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
