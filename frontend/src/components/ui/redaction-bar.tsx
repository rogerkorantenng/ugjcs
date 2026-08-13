import { formatAuthors } from "@/lib/format";

/**
 * The app's one signature device, built from the physical act at the heart of double-blind
 * review. Reviewer-facing screens render this with no `names` — a solid `ink` block, hatched
 * like something physically blacked out, labelled "Author withheld". The public archive
 * renders the exact same shape with `names` supplied, so the block opens into a plain byline
 * instead. A reader who has seen both instantly understands the mechanic the whole system is
 * built on — that is deliberate, and it is why this component is shared rather than two
 * unrelated pieces of markup that happen to sit in the same place.
 *
 * `BlindedManuscript` (the type this renders against on every reviewer-facing screen) has no
 * author field at all — this component is never handed real identity to hide, it only ever
 * renders the redacted variant. The revealing variant is reachable exclusively from
 * `ArchivePaperOut.author_names`, a field that exists only on the public, post-publication
 * archive shape.
 */
export function RedactionBar({ names, compact = false }: { names?: string[]; compact?: boolean }) {
  const size = compact ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  if (!names) {
    return (
      <p
        className={`redaction-hatch inline-flex items-center gap-1.5 rounded-[2px] bg-ink font-mono uppercase tracking-[0.14em] text-paper ${size}`}
      >
        <span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 rounded-full bg-stamp" />
        Author withheld
        <span className="sr-only"> — identity blinded for double-blind review</span>
      </p>
    );
  }

  return (
    <p
      className={`inline-flex items-center gap-1.5 rounded-[2px] border border-stamp/25 bg-stamp/[0.05] font-mono uppercase tracking-[0.14em] text-stamp ${size}`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 rounded-full bg-stamp" />
      {formatAuthors(names)}
    </p>
  );
}
