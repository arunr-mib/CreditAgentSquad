import { RadioGroup } from 'radix-ui';
import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

export interface Choice {
  value: string;
  label: string;
  hint?: ReactNode;
}

export interface ChoiceCardsProps {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  choices: Choice[];
  disabled?: boolean;
  name?: string;
}

/** A single choice set out as cards a person can press anywhere on. A radio group underneath. */
export function ChoiceCards({ label, value, onValueChange, choices, disabled, name }: ChoiceCardsProps) {
  return (
    <RadioGroup.Root aria-label={label} name={name} value={value} onValueChange={onValueChange} disabled={disabled} className="grid gap-2">
      {choices.map((choice) => (
        <RadioGroup.Item
          key={choice.value}
          value={choice.value}
          className={cx(
            'group flex w-full items-start gap-3 rounded-md border border-hairline-strong bg-surface px-3 py-2.5 text-left t-colors',
            'hover:border-ink-400 hover:bg-hover',
            'data-[state=checked]:border-cobalt data-[state=checked]:bg-cobalt-bg',
            'disabled:opacity-60 disabled:hover:border-hairline-strong disabled:hover:bg-surface',
          )}
        >
          <span
            aria-hidden
            className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border-[1.5px] border-ink-400 bg-surface group-data-[state=checked]:border-cobalt"
          >
            <RadioGroup.Indicator className="size-2 rounded-full bg-cobalt" />
          </span>
          <span className="min-w-0">
            <span className="block text-body font-medium text-ink">{choice.label}</span>
            {choice.hint ? <span className="block text-caption text-pretty text-ink-700">{choice.hint}</span> : null}
          </span>
        </RadioGroup.Item>
      ))}
    </RadioGroup.Root>
  );
}
