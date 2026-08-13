import type { TourStep } from "./tour";

/**
 * Role-specific tour scripts. Each dashboard page mounts `<Tour>` with its own definition;
 * the storage key is versioned per role so a future rewrite of a script (bump to `-v2`)
 * re-offers the tour without disturbing the other roles.
 *
 * Steps with a `target` anchor to a `data-tour` attribute on the dashboard; steps without
 * one are concept cards (anonymity, the editorial process) shown centred. Anchored steps
 * whose element is absent — an empty dashboard, say — are skipped at start.
 */
interface TourDefinition {
  storageKey: string;
  steps: TourStep[];
}

export const AUTHOR_TOUR: TourDefinition = {
  storageKey: "ugjcs-tour-author-v2",
  steps: [
    {
      target: "author-welcome",
      title: "Your submissions desk",
      body: "Welcome to the SDJ editorial portal. Every manuscript you send to the journal is tracked from this page — one card per submission, from first upload to final decision.",
    },
    {
      target: "author-submit",
      title: "Submit a manuscript",
      body: "Start here when a paper is ready. You upload an anonymised PDF, list any co-authors, and receive a tracking code the moment the manuscript is received.",
    },
    {
      target: "author-list",
      title: "Follow each manuscript",
      body: "The status chip on the right shows where a manuscript stands — under screening, out for review, revision requested. Click a card to read the reviews, resubmit a revision, view your PDF, or withdraw.",
    },
    {
      target: "author-tracking",
      title: "Tracking codes",
      body: "Every submission is stamped with a code like this. It identifies your paper throughout review without revealing who wrote it — quote it in any correspondence with the editors.",
    },
  ],
};

export const REVIEWER_TOUR: TourDefinition = {
  storageKey: "ugjcs-tour-reviewer-v2",
  steps: [
    {
      target: "reviewer-welcome",
      title: "Your review desk",
      body: "Welcome. Manuscripts an editor has asked you to review are collected on this page, each under the tracking code the journal uses to refer to it.",
    },
    {
      target: "reviewer-list",
      title: "Assignments awaiting you",
      body: "Each card is one manuscript waiting on your review. It stays in this list until you have submitted your scores and comments.",
    },
    {
      title: "Double-blind, both ways",
      body: "Reviews at the Science and Development Journal are fully anonymised: author names, affiliations, and acknowledgements are redacted before a paper reaches you, and authors never learn who reviewed them. You judge the work, not the names.",
    },
    {
      target: "reviewer-card",
      title: "Open an assignment",
      body: "Click a card to open the review form with the anonymised PDF inline beside it. Score the manuscript, write your comments for the authors and the editor, and submit.",
    },
  ],
};

export const EDITOR_TOUR: TourDefinition = {
  storageKey: "ugjcs-tour-editor-v2",
  steps: [
    {
      target: "editor-welcome",
      title: "The editorial queue",
      body: "Welcome. Every manuscript that needs editorial attention passes through this page — nothing leaves the queue until it is published, rejected, or withdrawn.",
    },
    {
      target: "editor-queue",
      title: "Grouped by stage",
      body: "Manuscripts are grouped by where they stand in the process, with a hint under each heading for what to do next. Click a tracking code or title to open the full record.",
    },
    {
      title: "Screening",
      body: "New submissions arrive as awaiting screening. Open one to check scope, formatting, and anonymisation, then either desk-reject it or send it on to peer review.",
    },
    {
      title: "Assigning reviewers",
      body: "From a manuscript's page you choose its reviewers. The picker also lists candidates who are excluded — a co-authorship or shared affiliation, say — and states exactly why, so the double-blind stays intact.",
    },
    {
      title: "Recording decisions",
      body: "Once the reviews are in, the manuscript moves to reviews complete. Read the scores and comments, then record your decision: accept, request a revision, or reject.",
    },
    {
      title: "Publishing",
      body: "Accepted papers wait for the Editor-in-Chief to schedule them into an issue. Publishing assigns the final citation details and moves the paper into the public archive.",
    },
  ],
};
