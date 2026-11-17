import type { ReactNode } from 'react';

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-xs border border-hairline-strong bg-surface px-1 font-sans text-micro font-medium text-ink-700">
      {children}
    </kbd>
  );
}
