/** The journal's one recurring signature detail — every reference to a manuscript's
 * tracking code renders through here, never as an inline `font-mono` span written by hand.
 * The violet border and very slight rotation are a quiet echo of the registry stamp a
 * received manuscript is marked with — restrained everywhere it appears, so the fuller
 * stamp treatment (see `RegistryStamp`) still reads as the one place that motif is played
 * up in full. */
export function TrackingChip({ code, className = "" }: { code: string; className?: string }) {
  return (
    <span
      className={`inline-block -rotate-1 whitespace-nowrap rounded-[2px] border border-stamp/35 bg-stamp/[0.05] px-1.5 py-0.5 font-mono text-xs
        font-medium tracking-wider text-stamp ${className}`}
    >
      {code}
    </span>
  );
}
