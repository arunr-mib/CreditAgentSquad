import { Check, ChevronDown } from 'lucide-react';
import { Select as RadixSelect } from 'radix-ui';
import { useId } from 'react';
import { cx } from '@/lib/cx';
import { fieldLabelClass } from './Input';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  label: string;
  hideLabel?: boolean;
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
  size?: 'md' | 'sm';
}

export function Select({ label, hideLabel, value, onValueChange, options, className, size = 'md' }: SelectProps) {
  const id = useId();
  return (
    <div className={className}>
      <label id={`${id}-label`} htmlFor={id} className={hideLabel ? 'sr-only' : fieldLabelClass}>
        {label}
      </label>
      <RadixSelect.Root value={value} onValueChange={onValueChange}>
        <RadixSelect.Trigger
          id={id}
          aria-label={hideLabel ? label : undefined}
          className={cx(
            'flex w-full items-center justify-between gap-2 rounded-sm border border-ink-400 bg-surface px-2.5 text-body text-ink t-colors',
            'hover:border-ink-500 data-[state=open]:border-cobalt',
            size === 'md' ? 'h-8' : 'h-7',
          )}
        >
          <span className="whitespace-nowrap">
            <RadixSelect.Value />
          </span>
          <RadixSelect.Icon className="text-ink-500">
            <ChevronDown size={14} aria-hidden />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content
            position="popper"
            sideOffset={4}
            collisionPadding={8}
            className="anim-pop z-50 max-h-[min(var(--radix-select-content-available-height),420px)] min-w-(--radix-select-trigger-width) rounded-md border border-hairline-strong bg-surface p-1 shadow-raised"
          >
            <RadixSelect.Viewport>
              {options.map((option) => (
                <RadixSelect.Item
                  key={option.value}
                  value={option.value}
                  className="flex h-8 cursor-pointer items-center justify-between gap-6 rounded-xs px-2 text-body text-ink outline-none select-none data-[highlighted]:bg-cobalt-bg data-[state=checked]:font-medium"
                >
                  <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator>
                    <Check size={14} className="text-cobalt" aria-hidden />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </div>
  );
}
