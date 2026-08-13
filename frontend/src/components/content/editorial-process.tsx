import { NumberedStep, TermRow, TermList } from "./prose-page";

/** The six stages of a manuscript's life, in order — the /about page's core narrative,
 * kept as data so the page reads as an outline and the copy is edited in one place. */
const STEPS = [
  {
    title: "Submission",
    body: "The corresponding author submits a title, abstract, keywords and a PDF manuscript, and adds any co-authors by email. The portal issues a tracking code (for example SDJ-2026-0012) that identifies the manuscript for its whole life.",
  },
  {
    title: "Screening",
    body: "An editor reads the submission and decides whether it is in scope and complete enough to review. Manuscripts that clearly fall outside the journal's scope are desk-rejected at this stage, before any reviewer's time is spent; everything else goes to review.",
  },
  {
    title: "Double-blind review",
    body: "Two independent reviewers each read an anonymised copy of the manuscript — the byline is withheld and author-identifying metadata is stripped from the file automatically. Reviewers do not learn who the authors are, and authors never learn who reviewed them. Each reviewer returns a recommendation with written comments.",
  },
  {
    title: "Decision",
    body: "Once both reviews are in, the handling editor weighs them and records one of four decisions: accept, minor revision, major revision, or reject. The decision, with the reviewers' comments to the authors, goes back to the corresponding author.",
  },
  {
    title: "Revision and resubmission",
    body: "A revision decision is an invitation, not a rejection: the authors revise the manuscript and resubmit it under the same tracking code. The resubmission returns to the editor and is sent out for a fresh round of review, so a revised paper is judged again on its merits — not waved through.",
  },
  {
    title: "Publication",
    body: "Accepted manuscripts are scheduled into an issue and published to the open archive, where the full text is readable by anyone, with the authors' names restored to the byline.",
  },
];

export function EditorialProcess() {
  return (
    <ol className="mt-6 space-y-6">
      {STEPS.map((step, index) => (
        <NumberedStep key={step.title} index={index + 1} title={step.title}>
          <p>{step.body}</p>
        </NumberedStep>
      ))}
    </ol>
  );
}

const DECISIONS = [
  {
    term: "Accept",
    body: "The manuscript is publishable as it stands. It moves on to scheduling and publication.",
  },
  {
    term: "Minor revision",
    body: "The substance is sound but specific points need fixing — clarifications, missing detail, presentation. A revised version is expected to satisfy the reviewers' comments without changing the core of the work.",
  },
  {
    term: "Major revision",
    body: "The work is promising but something substantial must change — additional experiments, reworked analysis, a restructured argument. The revised manuscript goes through a full new round of review.",
  },
  {
    term: "Reject",
    body: "The manuscript will not be published in the journal, either at screening (desk rejection) or after review. Rejection is final for that manuscript.",
  },
];

export function DecisionGlossary() {
  return (
    <TermList>
      {DECISIONS.map((decision) => (
        <TermRow key={decision.term} term={decision.term}>
          {decision.body}
        </TermRow>
      ))}
    </TermList>
  );
}
