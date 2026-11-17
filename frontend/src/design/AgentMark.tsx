import { cx } from '@/lib/cx';

/**
 * The agent mark: an iris lozenge. It sits wherever text was written by an agent,
 * the way a colleague's initials sit beside a margin note.
 */
export function AgentMark({ size = 10, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" aria-hidden className={cx('shrink-0 text-iris-mark', className)} fill="currentColor">
      <path d="M5 0 10 5 5 10 0 5Z" />
    </svg>
  );
}
