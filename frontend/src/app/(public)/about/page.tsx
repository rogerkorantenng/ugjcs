import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage, ProseSection } from "@/components/content/prose-page";
import { EditorialProcess, DecisionGlossary } from "@/components/content/editorial-process";

export const metadata: Metadata = {
  title: "About the journal",
  description:
    "Aims and scope of the University of Ghana Journal of Computing Science, and how its double-blind editorial process works, step by step.",
};

const link = "font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp";

export default function AboutPage() {
  return (
    <ProsePage
      eyebrow="About the journal"
      title="About UGJCS"
      lede="The University of Ghana Journal of Computing Science publishes original research in computing and information systems — from the Department of Computer Science at Legon, and from the wider research community. Every paper in the archive has passed the same route: screening, two independent double-blind reviews, and an editorial decision."
    >
      <ProseSection title="Aims and scope">
        <p>
          UGJCS considers full-length research papers across computing science: algorithms and theory, software
          engineering, information systems, data science and machine learning, networks and security, and
          human-computer interaction. We are particularly interested in work that applies computing to problems
          relevant in Ghana and across West Africa — but sound research is welcome wherever it comes from.
        </p>
        <p>
          We publish work that is original, technically correct, and clearly argued. Surveys and position papers
          are considered when they organise a field in a way a working researcher can build on; incremental
          restatements of published results are not.
        </p>
      </ProseSection>

      <ProseSection title="How a manuscript moves through the journal">
        <p>
          The process is deliberately simple, and every stage of it is visible to the author through the
          manuscript&rsquo;s status. From submission to decision:
        </p>
        <EditorialProcess />
      </ProseSection>

      <ProseSection title="What each decision means">
        <DecisionGlossary />
      </ProseSection>

      <ProseSection title="Open access">
        <p>
          UGJCS is an open-access journal. Every published paper is readable in full by anyone, free of charge —
          no subscription, no paywall, and no reader registration. There are also no fees on the author side:
          submission and publication cost nothing, and authors retain the copyright to their work.
        </p>
      </ProseSection>

      <ProseSection title="A note on this site">
        <p>
          UGJCS is a fictional journal, built as coursework for an Advanced Software Engineering exam. The
          editorial workflow described on this page — submission, screening, double-blind review, decisions,
          resubmission and publication — is real and fully working in this system, but the journal is not an
          official University of Ghana publication, and the papers in the archive are demonstration content.
        </p>
      </ProseSection>

      <div className="mt-10 border-t border-rule pt-8 text-sm">
        <p className="text-ink/60">
          Thinking of submitting, or been invited to review?{" "}
          <Link href="/for-authors" className={link}>Read the author guidelines</Link> or the{" "}
          <Link href="/for-reviewers" className={link}>reviewer guidelines</Link>.
        </p>
      </div>
    </ProsePage>
  );
}
