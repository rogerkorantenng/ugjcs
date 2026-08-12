/** The journal's one recurring signature detail — every reference to a manuscript's
 * tracking code renders through here, never as an inline `font-mono` span written by hand. */
export function TrackingChip({ code, className = "" }: { code: string; className?: string }) {
  return (
    <span
      className={`inline-block rounded-[3px] border border-rule px-1.5 py-0.5 font-mono text-xs
        tracking-wider text-ink/70 ${className}`}
    >
      {code}
    </span>
  );
}
