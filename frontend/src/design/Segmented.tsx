import { ToggleGroup } from 'radix-ui';
import { cx } from '@/lib/cx';

export interface SegmentedOption {
  value: string;
  label: string;
  count?: number;
}

export interface SegmentedProps {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  options: SegmentedOption[];
}

/** A single-choice filter. Square-shouldered segments joined by hairlines. */
export function Segmented({ label, value, onValueChange, options }: SegmentedProps) {
  return (
    <ToggleGroup.Root
      type="single"
      aria-label={label}
      value={value}
      onValueChange={(next) => {
        if (next) onValueChange(next);
      }}
      className="inline-flex h-8 items-stretch rounded-sm border border-hairline-strong bg-surface"
    >
      {options.map((option, index) => (
        <ToggleGroup.Item
          key={option.value}
          value={option.value}
          className={cx(
            'inline-flex items-center gap-1.5 px-3 text-body font-medium text-ink-700 t-colors',
            'hover:bg-hover hover:text-ink',
            'data-[state=on]:bg-ink data-[state=on]:text-canvas',
            index > 0 && 'border-l border-hairline-strong',
            index === 0 && 'rounded-l-[3px]',
            index === options.length - 1 && 'rounded-r-[3px]',
          )}
        >
          {option.label}
          {option.count !== undefined ? <span className="tnum text-caption opacity-80">{option.count}</span> : null}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}
