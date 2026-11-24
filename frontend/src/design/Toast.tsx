import { X } from 'lucide-react';
import { Toast as RadixToast } from 'radix-ui';
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { StatusDot, type StatusTone } from './StatusDot';

export interface ToastMessage {
  title: string;
  description?: string;
  /** 'pass' only for a recorded decision or a verified result. Default is neutral. */
  tone?: StatusTone;
}

interface ToastEntry extends ToastMessage {
  id: number;
}

const ToastContext = createContext<(message: ToastMessage) => void>(() => {});

export function useToast(): (message: ToastMessage) => void {
  return useContext(ToastContext);
}

/** Confirms that something was recorded. Never the only record: the ledger is. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);
  const push = useCallback((message: ToastMessage) => {
    setToasts((current) => [...current, { ...message, id: Date.now() + Math.random() }]);
  }, []);
  const value = useMemo(() => push, [push]);

  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider duration={6000} swipeDirection="right" label="Notification">
        {children}
        {toasts.map((toast) => (
          <RadixToast.Root
            key={toast.id}
            onOpenChange={(open) => {
              if (!open) setToasts((current) => current.filter((entry) => entry.id !== toast.id));
            }}
            className="anim-rise flex w-[360px] items-start gap-3 rounded-md border border-hairline-strong bg-surface px-4 py-3 shadow-raised"
          >
            <div className="min-w-0 flex-1">
              <RadixToast.Title className="text-body font-semibold text-ink">
                <StatusDot tone={toast.tone ?? 'neutral'}>{toast.title}</StatusDot>
              </RadixToast.Title>
              {toast.description ? (
                <RadixToast.Description className="mt-0.5 pl-[13px] text-caption text-ink-700">{toast.description}</RadixToast.Description>
              ) : null}
            </div>
            <RadixToast.Close
              aria-label="Dismiss"
              className="-mr-1.5 inline-flex size-6 shrink-0 items-center justify-center rounded-sm text-ink-500 t-colors hover:bg-hover hover:text-ink"
            >
              <X size={14} aria-hidden />
            </RadixToast.Close>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className="fixed right-6 bottom-6 z-[60] flex flex-col gap-2 outline-none" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}
