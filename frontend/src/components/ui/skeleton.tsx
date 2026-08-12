/** A single placeholder bar. Compose several into a shape that mirrors the content being
 * replaced — a skeleton should read as "the outline of the thing that's coming", not as a
 * generic spinner. Always `aria-hidden`: the loading announcement belongs to the
 * `role="status"` region that wraps a composed skeleton, not to each individual bar. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-[3px] bg-ink/10 ${className}`} />;
}
