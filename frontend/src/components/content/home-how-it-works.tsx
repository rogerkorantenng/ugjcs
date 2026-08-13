import Link from "next/link";

const STEPS = [
  {
    title: "Submit",
    body: "An author signs in and submits a title, abstract, keywords and a PDF manuscript, adding co-authors by email. The portal issues a tracking code — like SDJ-2026-0012 — that follows the manuscript for life.",
    href: "/for-authors",
    linkLabel: "Read the author guidelines",
  },
  {
    title: "Double-blind review",
    body: "After an editor screens it, two independent reviewers read an anonymised copy — byline withheld, identifying metadata stripped by the portal. The editor weighs their reports and decides: accept, revise, or reject.",
    href: "/for-reviewers",
    linkLabel: "Read the reviewer guidelines",
  },
  {
    title: "Publish",
    body: "Accepted manuscripts are scheduled into an issue and published to the open archive, byline restored, full text free for anyone to read. Revised papers return for a fresh review round first.",
    href: "/about",
    linkLabel: "How the portal works",
  },
];

/** Front-matter, not marketing: the portal's three-stage editorial route in the same
 * numbered-list language, each column ending in the guidance page that covers it. */
export function HowItWorks() {
  return (
    <section aria-labelledby="how-it-works" className="border-t border-rule bg-surface/40">
      <div className="mx-auto max-w-5xl px-4 py-14">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">How it works</p>
        <h2 id="how-it-works" className="font-display-heading mt-2 text-xl font-semibold text-ink">
          From submission to the archive
        </h2>
        <div className="mt-8 grid gap-10 sm:grid-cols-3 sm:gap-8">
          {STEPS.map((step, index) => (
            <div key={step.title} className="min-w-0">
              <span aria-hidden="true" className="font-mono text-2xl font-light leading-none text-stamp/50 tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3 className="font-display-heading mt-3 text-base font-semibold text-ink">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/70">{step.body}</p>
              <Link
                href={step.href}
                className="mt-3 inline-block text-sm font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp"
              >
                {step.linkLabel} →
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
