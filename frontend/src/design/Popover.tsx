import { Popover as RadixPopover } from 'radix-ui';
import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

export interface PopoverProps {
  trigger: ReactNode;
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  className?: string;
  /** Accessible name for the popover panel. */
  label: string;
}

export const popoverSurfaceClass = 'anim-pop z-50 rounded-md border border-hairline-strong bg-surface shadow-raised outline-none';

export function Popover({ trigger, children, open, onOpenChange, side = 'bottom', align = 'start', className, label }: PopoverProps) {
  return (
    <RadixPopover.Root open={open} onOpenChange={onOpenChange}>
      <RadixPopover.Trigger asChild>{trigger}</RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content side={side} align={align} sideOffset={6} collisionPadding={12} aria-label={label} className={cx(popoverSurfaceClass, className)}>
          {children}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
