/**
 * The mark: three units in formation on an ink ground. The wordmark is set in Inter semibold.
 */
export function Mark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden className="shrink-0">
      <rect width="20" height="20" rx="4" className="fill-ink" />
      <rect x="4.5" y="10.5" width="4" height="4" className="fill-canvas" />
      <rect x="8" y="5.5" width="4" height="4" className="fill-canvas" />
      <rect x="11.5" y="10.5" width="4" height="4" className="fill-canvas" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Mark />
      <span className="hidden text-prose font-semibold tracking-[-0.012em] whitespace-nowrap text-ink lg:inline">Credit Agent Squad</span>
    </span>
  );
}
