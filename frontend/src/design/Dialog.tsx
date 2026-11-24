import { X } from 'lucide-react';
import { Dialog as RadixDialog } from 'radix-ui';
import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

export interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
  title: string;
  description?: string;
  children?: ReactNode;
  /** Footer actions. One primary button at most. */
  footer?: ReactNode;
  width?: 'sm' | 'md';
}

export const overlayClass = 'anim-fade fixed inset-0 z-40 bg-ink/35';

export function Dialog({ open, onOpenChange, trigger, title, description, children, footer, width = 'sm' }: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger ? <RadixDialog.Trigger asChild>{trigger}</RadixDialog.Trigger> : null}
      <RadixDialog.Portal>
        <RadixDialog.Overlay className={overlayClass} />
        <RadixDialog.Content
          {...(description ? {} : { 'aria-describedby': undefined })}
          className={cx(
            'anim-rise fixed top-[18vh] left-1/2 z-50 -translate-x-1/2 rounded-md border border-hairline-strong bg-surface shadow-overlay',
            width === 'sm' ? 'w-[480px]' : 'w-[640px]',
          )}
        >
          <div className="flex items-start justify-between gap-4 px-5 pt-4">
            <div>
              <RadixDialog.Title className="text-title font-semibold text-ink">{title}</RadixDialog.Title>
              {description ? <RadixDialog.Description className="mt-1 text-body text-ink-700">{description}</RadixDialog.Description> : null}
            </div>
            <RadixDialog.Close
              aria-label="Close"
              className="-mr-1.5 inline-flex size-7 shrink-0 items-center justify-center rounded-sm text-ink-500 t-colors hover:bg-hover hover:text-ink"
            >
              <X size={16} aria-hidden />
            </RadixDialog.Close>
          </div>
          {children ? <div className="px-5 pt-4">{children}</div> : null}
          <div className="mt-5 flex items-center justify-end gap-2 border-t border-hairline px-5 py-3">{footer}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

export const DialogClose = RadixDialog.Close;
