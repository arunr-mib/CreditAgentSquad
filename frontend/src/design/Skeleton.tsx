import { cx } from '@/lib/cx';

/** A still placeholder. Skeletons do not shimmer: no animation runs longer than 240 ms. */
export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden className={cx('block rounded-xs bg-sunken', className ?? 'h-3 w-24')} />;
}

export function SkeletonRows({ rows = 6, label = 'Loading' }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="rounded-md border border-hairline-strong bg-surface">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex h-[34px] items-center gap-6 border-b border-hairline px-3 last:border-b-0">
          <Skeleton className="h-2.5 w-40" />
          <Skeleton className="h-2.5 w-64" />
          <span className="flex-1" />
          <Skeleton className="h-2.5 w-16" />
          <Skeleton className="h-2.5 w-16" />
        </div>
      ))}
    </div>
  );
}
