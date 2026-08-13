/**
 * This app's one signature device. Where an author's name would sit, a reviewer sees a
 * solid ink block labelled "Author withheld" — the double-blind mechanic made visible, not
 * just enforced silently by a type with no author field. The public archive renders the
 * *same slot*, same label position, same border geometry, with the actual byline in place
 * of the block (`revealed` below) — seeing both teaches the mechanic at a glance, the way a
 * censored and an uncensored document rhyme.
 *
 * Deliberately not reused for anything else in the app: one memorable device, kept rare.
 */

const SLOT_BASE = "flex items-center gap-3 rounded-[2px] border border-rule px-3 py-2.5";

export function RedactedAuthorSlot({ className = "" }: { className?: string }) {
  return (
    <div className={`${SLOT_BASE} border-ink/15 bg-ink/[0.02] ${className}`}>
      <span
        aria-hidden="true"
        className="bg-redaction h-4 w-32 shrink-0 rounded-[1px]"
      />
      <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-ink/50">
        Author withheld — double-blind review
      </span>
    </div>
  );
}

export function RevealedAuthorSlot({ names, className = "" }: { names: string[]; className?: string }) {
  return (
    <div className={`${SLOT_BASE} border-stamp/25 bg-stamp/[0.04] ${className}`}>
      <span className="font-sans text-sm font-medium text-ink" data-testid="revealed-author-names">
        {names.length > 0 ? names.join(", ") : "Unattributed"}
      </span>
      <span className="ml-auto shrink-0 font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-stamp/70">
        Author of record
      </span>
    </div>
  );
}
