import { X } from 'lucide-react';
import { Dialog as RadixDialog } from 'radix-ui';
import { useEffect, useRef, type ReactNode } from 'react';
import { cx } from '@/lib/cx';

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Accessible name of the drawer. */
  title: string;
  /** Shown in the header, left of the close button: usually a segmented switch. */
  header?: ReactNode;
  children?: ReactNode;
  className?: string;
}

/**
 * A slide-over on the right edge. Not modal: the page behind stays in use, so a person can move
 * down a queue while the drawer follows. On a phone it is a full-screen sheet above the bottom bar.
 */
export function Drawer({ open, onOpenChange, title, header, children, className }: DrawerProps) {
  const content = useRef<HTMLDivElement>(null);
  // Where focus was on the page, outside the drawer: Esc or the close button gives it back there.
  // The drawer has no trigger of its own (a queue row, a button or a link opens it), so without
  // this, closing it from inside drops focus on the document body.
  const returnTo = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    if (document.activeElement instanceof HTMLElement && document.activeElement !== document.body) returnTo.current = document.activeElement;
    const note = (event: FocusEvent) => {
      if (event.target instanceof HTMLElement && !content.current?.contains(event.target)) returnTo.current = event.target;
    };
    document.addEventListener('focusin', note);
    return () => document.removeEventListener('focusin', note);
  }, [open]);

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange} modal={false}>
      <RadixDialog.Portal>
        <RadixDialog.Content
          ref={content}
          aria-describedby={undefined}
          data-drawer
          onInteractOutside={(event) => event.preventDefault()}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => {
            const target = returnTo.current;
            returnTo.current = null;
            if (target?.isConnected) {
              event.preventDefault();
              target.focus({ preventScroll: true });
            }
          }}
          className={cx(
            'anim-slide fixed top-[var(--topbar-h)] right-0 bottom-0 z-30 flex w-[var(--drawer-w)] flex-col border-l border-hairline-strong bg-surface shadow-overlay outline-none',
            'max-sm:top-0 max-sm:bottom-[calc(56px+env(safe-area-inset-bottom))] max-sm:w-full max-sm:max-w-none max-sm:border-l-0',
            className,
          )}
        >
          <div className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-hairline px-3">
            <RadixDialog.Title className="sr-only">{title}</RadixDialog.Title>
            <div className="flex min-w-0 flex-1 items-center gap-2">{header}</div>
            <RadixDialog.Close
              aria-label={`Close ${title}`}
              className="inline-flex size-8 shrink-0 items-center justify-center rounded-sm text-ink-500 t-colors hover:bg-hover hover:text-ink"
            >
              <X size={16} aria-hidden />
            </RadixDialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
