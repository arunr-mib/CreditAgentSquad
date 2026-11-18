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

/** The mark with the product's name and the lender's beneath it; the mark alone where there is no room for words. */
export function Wordmark({ markOnly = false }: { markOnly?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Mark size={22} />
      {markOnly ? null : (
        <span className="whitespace-nowrap">
          <span className="block text-body/4 font-semibold tracking-[-0.012em] text-ink">Credit Agent Squad</span>
          {/* A space between the two lines, so the text read out is "Credit Agent Squad Bank of Stoic", not run together. */}{' '}
          <span className="block text-micro/4 text-ink-500">Bank of Stoic</span>
        </span>
      )}
    </span>
  );
}
