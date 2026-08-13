import type { ReactNode } from "react";

/**
 * Shell for the public long-form pages (/about, /for-authors, /for-reviewers): the same
 * mono eyebrow → display-face h1 → lede opening the paper detail page uses, at the same
 * `max-w-3xl` measure, so a guidance page reads as another page of the journal rather than
 * a separate marketing site. Server-safe: static markup only.
 */
export function ProsePage({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">{eyebrow}</p>
      <h1 className="font-display-heading mt-3 text-3xl font-semibold leading-tight tracking-tight text-ink">
        {title}
      </h1>
      <p className="mt-4 max-w-prose text-lg leading-relaxed text-ink/70">{lede}</p>
      {children}
    </main>
  );
}

/** A titled section separated by the journal's hairline rule — the print convention of a
 * rule between front-matter sections, not a card or a coloured band. */
export function ProseSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-10 border-t border-rule pt-8">
      <h2 className="font-display-heading text-xl font-semibold text-ink">{title}</h2>
      <div className="mt-4 space-y-4 text-[0.95rem] leading-relaxed text-ink/75">{children}</div>
    </section>
  );
}

/** One entry in a numbered process — reuses the homepage contents-list numbering (a light
 * mono numeral in the stamp colour), because these steps, like published papers, have a
 * real order rather than a decorative one. */
export function NumberedStep({
  index,
  title,
  children,
}: {
  index: number;
  title: string;
  children: ReactNode;
}) {
  return (
    <li className="grid grid-cols-[3rem_1fr] gap-4">
      <span aria-hidden="true" className="font-mono text-2xl font-light leading-none text-stamp/50 tabular-nums">
        {String(index).padStart(2, "0")}
      </span>
      <div className="min-w-0">
        <h3 className="font-display-heading text-base font-semibold text-ink">{title}</h3>
        <div className="mt-1 space-y-2 text-sm leading-relaxed text-ink/70">{children}</div>
      </div>
    </li>
  );
}

/** A term/definition row for glossary-style lists (decisions, statuses): mono tracked term
 * on the left, plain-words definition on the right, rows divided by the hairline rule. */
export function TermRow({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr] sm:gap-4">
      <dt className="font-mono text-xs uppercase tracking-[0.14em] text-stamp">{term}</dt>
      <dd className="text-sm leading-relaxed text-ink/75">{children}</dd>
    </div>
  );
}

/** Wrapper for a run of `TermRow`s. */
export function TermList({ children }: { children: ReactNode }) {
  return <dl className="divide-y divide-rule border-y border-rule">{children}</dl>;
}
