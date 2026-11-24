import type { ButtonHTMLAttributes, ReactNode, Ref } from 'react';
import { cx } from '@/lib/cx';
import { Tooltip } from './Tooltip';

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label'> {
  /** Required: the accessible name, also shown as the tooltip. */
  label: string;
  icon: ReactNode;
  size?: 'md' | 'sm';
  tooltipSide?: 'top' | 'right' | 'bottom' | 'left';
  ref?: Ref<HTMLButtonElement>;
}

export function IconButton({ label, icon, size = 'md', tooltipSide, className, type, ...rest }: IconButtonProps) {
  return (
    <Tooltip content={label} side={tooltipSide}>
      <button
        type={type ?? 'button'}
        aria-label={label}
        className={cx(
          'inline-flex shrink-0 items-center justify-center rounded-sm text-ink-700 t-colors hover:bg-hover hover:text-ink disabled:opacity-50',
          size === 'md' ? 'size-8' : 'size-7',
          className,
        )}
        {...rest}
      >
        {icon}
      </button>
    </Tooltip>
  );
}
