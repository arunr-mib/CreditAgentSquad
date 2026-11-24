import { Tooltip as RadixTooltip } from 'radix-ui';
import { useState, type ReactNode } from 'react';

export const TooltipProvider = RadixTooltip.Provider;

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  /** Never opens. For a control whose name is already written beside it; the control stays mounted either way. */
  disabled?: boolean;
  /** Milliseconds before it opens. Defaults to the provider's delay. */
  delay?: number;
}

/** Names a control or explains a mark. Never the only place a fact or instruction lives. */
export function Tooltip({ content, children, side = 'top', disabled = false, delay }: TooltipProps) {
  const [open, setOpen] = useState(false);
  return (
    <RadixTooltip.Root open={open && !disabled} onOpenChange={setOpen} delayDuration={delay}>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          sideOffset={6}
          collisionPadding={8}
          className="anim-fade z-50 max-w-64 rounded-sm bg-ink px-2 py-1 text-caption font-medium text-canvas"
        >
          {content}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
