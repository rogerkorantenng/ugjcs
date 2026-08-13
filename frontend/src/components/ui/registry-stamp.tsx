/**
 * The fuller registry-stamp treatment — a double-ringed, slightly rotated mark in the
 * violet "stamp" ink, styled after the accession stamp a received manuscript is physically
 * marked with. Used sparingly, at the head of a manuscript's detail record and framing its
 * PDF viewer, never in a list: a stamp appears once per document, not once per row (that
 * quieter job belongs to `TrackingChip`).
 */
export function RegistryStamp({ code, className = "" }: { code: string; className?: string }) {
  return (
    <div
      className={`inline-flex -rotate-2 flex-col items-center gap-0.5 rounded-[2px] border-2 border-stamp px-3 py-1.5
        text-stamp shadow-[inset_0_0_0_2px_var(--color-paper),inset_0_0_0_3px_var(--color-stamp)] ${className}`}
    >
      <span aria-hidden="true" className="font-mono text-[9px] font-semibold uppercase tracking-[0.3em]">Accession</span>
      <span className="font-mono text-xs font-semibold tracking-wider">{code}</span>
    </div>
  );
}
