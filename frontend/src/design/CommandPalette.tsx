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
  /** Secondary text on the right, or beneath the label where the row is narrow: an industry, a count, what the command does. */
  hint?: string;
  icon?: ReactNode;
  keywords?: string;
  /** Listed only once the person has typed something: for the long tail that would bury the short list. */
  searchOnly?: boolean;
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
    if (words.length === 0) return commands.filter((command) => !command.searchOnly);
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
          className="anim-rise fixed top-[6vh] left-1/2 z-50 w-[620px] -translate-x-1/2 overflow-hidden rounded-md border border-hairline-strong bg-surface shadow-overlay sm:top-[14vh]"
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
            <span aria-hidden className="max-sm:hidden">
              <Kbd>Esc</Kbd>
            </span>
            <RadixDialog.Close className="link text-body font-medium sm:hidden">Close</RadixDialog.Close>
          </div>
          <div ref={listRef} id={listId} role="listbox" aria-label="Results" className="@container max-h-[min(440px,60vh)] overflow-y-auto p-1.5">
            {matches.length === 0 ? (
              <p className="px-3 py-6 text-body text-pretty text-ink-700">Nothing matches “{query}”. Try a borrower name, a section or a queue filter.</p>
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
                        className={cx('flex min-h-9 cursor-pointer items-start gap-2.5 rounded-sm px-2.5 py-2 text-body text-ink', selected && 'bg-cobalt-bg')}
                      >
                        {command.icon ? (
                          <span className={cx('flex h-5 shrink-0 items-center', selected ? 'text-cobalt-strong' : 'text-ink-500')}>{command.icon}</span>
                        ) : null}
                        {/* A long name or hint wraps onto its own line; nothing is cut short. */}
                        <span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-3 gap-y-0.5">
                          <span className="min-w-0 font-medium text-pretty">{command.label}</span>
                          {command.hint ? (
                            <span className="min-w-0 text-caption text-pretty text-ink-500 @min-[480px]:ml-auto @min-[480px]:text-right">{command.hint}</span>
                          ) : null}
                        </span>
                        <CornerDownLeft size={12} aria-hidden className={cx('mt-1 shrink-0 text-cobalt-strong', !selected && 'invisible')} />
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>
          <div className="flex items-center gap-4 border-t border-hairline px-4 py-2 text-caption text-ink-500 max-sm:hidden">
            <span className="inline-flex items-center gap-1.5">
              <Kbd>↑</Kbd>
              <Kbd>↓</Kbd> to move
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Kbd>Enter</Kbd> to choose
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Kbd>Esc</Kbd> to close
            </span>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
