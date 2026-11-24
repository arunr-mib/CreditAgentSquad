import { Slot } from 'radix-ui';
import type { ButtonHTMLAttributes, ReactNode, Ref } from 'react';
import { cx } from '@/lib/cx';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';
export type ButtonSize = 'md' | 'sm';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  /** Render the child element (for example a router link) with button styling. */
  asChild?: boolean;
  ref?: Ref<HTMLButtonElement>;
}

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-cobalt text-white border-transparent hover:bg-cobalt-strong active:bg-cobalt-strong',
  secondary: 'bg-surface text-ink border-hairline-strong hover:bg-hover hover:border-ink-400 active:bg-sunken',
  ghost: 'bg-transparent text-cobalt border-transparent hover:bg-cobalt-bg hover:text-cobalt-strong',
};

const sizes: Record<ButtonSize, string> = {
  md: 'h-8 px-3 text-body',
  sm: 'h-7 px-2.5 text-caption',
};

export function buttonClass(variant: ButtonVariant = 'secondary', size: ButtonSize = 'md', className?: string): string {
  return cx(
    'inline-flex shrink-0 items-center justify-center gap-1.5 rounded-sm border font-medium whitespace-nowrap select-none t-colors',
    'disabled:opacity-50 aria-disabled:opacity-50',
    variants[variant],
    sizes[size],
    className,
  );
}

/** One primary button per card or dialog: the one clear next action. Everything else is secondary or ghost. */
export function Button({ variant = 'secondary', size = 'md', iconLeft, iconRight, asChild, className, children, type, ...rest }: ButtonProps) {
  const classes = buttonClass(variant, size, className);
  if (asChild) {
    return (
      <Slot.Root className={classes} {...rest}>
        {children}
      </Slot.Root>
    );
  }
  return (
    <button type={type ?? 'button'} className={classes} {...rest}>
      {iconLeft}
      {children}
      {iconRight}
    </button>
  );
}
