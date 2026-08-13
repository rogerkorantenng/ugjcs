import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage, ProseSection, NumberedStep, TermRow, TermList } from "@/components/content/prose-page";

export const metadata: Metadata = {
  title: "About the journal",
  description:
    "Aims and scope of the University of Ghana Journal of Computing Science, and how its double-blind editorial process works, step by step.",
};

export default function AboutPage() {
  return (
    <ProsePage
      eyebrow="About the journal"
      title="About UGJCS"
      lede="The University of Ghana Journal of Computing Science publishes original research in computing and information systems — from the Department of Computer Science at Legon, and from the wider research community. Every paper in the archive has passed the same route: screening, two independent double-blind reviews, and an editorial decision."
    >
      <ProseSection title="Aims and scope">
        <p>
          UGJCS considers full-length research papers across computing science: algorithms and theory,
          software engineering, information systems, data science and machine learning, networks and
          security, and human-computer interaction. We are particularly interested in work that applies
          computing to problems relevant in Ghana and across West Africa — but sound research is welcome
          wherever it comes from.
        </p>
        <p>
          We publish work that is original, technically correct, and clearly argued. Surveys and
          position papers are considered when they organise a field in a way a working researcher can
          build on; incremental restatements of published results are not.
        </p>
      </ProseSection>

      <ProseSection title="How a manuscript moves through the journal">
        <p>
          The process is deliberately simple, and every stage of it is visible to the author through
          the manuscript&rsquo;s status. From submission to decision:
        </p>
        <ol className="mt-6 space-y-6">
          <NumberedStep index={1} title="Submission">
            <p>
              The corresponding author submits a title, abstract, keywords and a PDF manuscript, and
              adds any co-authors by email. The system issues a tracking code (for example
              UGJCS-2026-0012) that identifies the manuscript for its whole life.
            </p>
          </NumberedStep>
          <NumberedStep index={2} title="Screening">
            <p>
              An editor reads the submission and decides whether it is in scope and complete enough to
              review. Manuscripts that clearly fall outside the journal&rsquo;s scope are desk-rejected
              at this stage, before any reviewer&rsquo;s time is spent; everything else goes to review.
            </p>
          </NumberedStep>
          <NumberedStep index={3} title="Double-blind review">
            <p>
              Two independent reviewers each read an anonymised copy of the manuscript — the byline is
              withheld and author-identifying metadata is stripped from the file automatically.
              Reviewers do not learn who the authors are, and authors never learn who reviewed them.
              Each reviewer returns a recommendation with written comments.
            </p>
          </NumberedStep>
          <NumberedStep index={4} title="Decision">
            <p>
              Once both reviews are in, the handling editor weighs them and records one of four
              decisions: accept, minor revision, major revision, or reject. The decision, with the
              reviewers&rsquo; comments to the authors, goes back to the corresponding author.
            </p>
          </NumberedStep>
          <NumberedStep index={5} title="Revision and resubmission">
            <p>
              A revision decision is an invitation, not a rejection: the authors revise the manuscript
              and resubmit it under the same tracking code. The resubmission returns to the editor and
              is sent out for a fresh round of review, so a revised paper is judged again on its
              merits — not waved through.
            </p>
          </NumberedStep>
          <NumberedStep index={6} title="Publication">
            <p>
              Accepted manuscripts are scheduled into an issue and published to the open archive, where
              the full text is readable by anyone, with the authors&rsquo; names restored to the byline.
            </p>
          </NumberedStep>
        </ol>
      </ProseSection>

      <ProseSection title="What each decision means">
        <TermList>
          <TermRow term="Accept">
            The manuscript is publishable as it stands. It moves on to scheduling and publication.
          </TermRow>
          <TermRow term="Minor revision">
            The substance is sound but specific points need fixing — clarifications, missing detail,
            presentation. A revised version is expected to satisfy the reviewers&rsquo; comments
            without changing the core of the work.
          </TermRow>
          <TermRow term="Major revision">
            The work is promising but something substantial must change — additional experiments,
            reworked analysis, a restructured argument. The revised manuscript goes through a full new
            round of review.
          </TermRow>
          <TermRow term="Reject">
            The manuscript will not be published in UGJCS, either at screening (desk rejection) or
            after review. Rejection is final for that manuscript.
          </TermRow>
        </TermList>
      </ProseSection>

      <ProseSection title="Open access">
        <p>
          UGJCS is an open-access journal. Every published paper is readable in full by anyone, free of
          charge — no subscription, no paywall, and no reader registration. There are also no fees on
          the author side: submission and publication cost nothing, and authors retain the copyright to
          their work.
        </p>
      </ProseSection>

      <ProseSection title="A note on this site">
        <p>
          UGJCS is a fictional journal, built as coursework for an Advanced Software Engineering exam.
          The editorial workflow described on this page — submission, screening, double-blind review,
          decisions, resubmission and publication — is real and fully working in this system, but the
          journal is not an official University of Ghana publication, and the papers in the archive are
          demonstration content.
        </p>
      </ProseSection>

      <div className="mt-10 border-t border-rule pt-8 text-sm">
        <p className="text-ink/60">
          Thinking of submitting, or been invited to review?{" "}
          <Link href="/for-authors" className="font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp">
            Read the author guidelines
          </Link>{" "}
          or the{" "}
          <Link href="/for-reviewers" className="font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp">
            reviewer guidelines
          </Link>
          .
        </p>
      </div>
    </ProsePage>
  );
}
