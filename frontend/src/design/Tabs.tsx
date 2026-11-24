import { Tabs as RadixTabs } from 'radix-ui';
import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

/** Shared look for Radix tab triggers and for router links that act as section tabs. */
export const tabListClass = 'flex items-end gap-6 border-b border-hairline-strong';
export const tabClass = cx(
  'relative -mb-px inline-flex h-9 items-center gap-2 border-b-2 border-transparent text-body font-medium text-ink-500 t-colors',
  'hover:text-ink',
  'data-[state=active]:border-ink data-[state=active]:text-ink',
  'aria-[current=page]:border-ink aria-[current=page]:text-ink',
  'aria-disabled:text-ink-400 aria-disabled:hover:text-ink-400',
);

export interface TabItem {
  value: string;
  label: string;
  count?: number;
  content: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  label: string;
}

export function Tabs({ items, defaultValue, value, onValueChange, label }: TabsProps) {
  return (
    <RadixTabs.Root defaultValue={defaultValue ?? items[0]?.value} value={value} onValueChange={onValueChange}>
      <RadixTabs.List aria-label={label} className={tabListClass}>
        {items.map((item) => (
          <RadixTabs.Trigger key={item.value} value={item.value} className={tabClass}>
            {item.label}
            {item.count !== undefined ? <span className="tnum text-caption text-ink-500">{item.count}</span> : null}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {items.map((item) => (
        <RadixTabs.Content key={item.value} value={item.value} className="pt-4">
          {item.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}
