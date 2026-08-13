import { TermRow, TermList } from "./prose-page";

/** The four things a submission consists of — rendered as the /for-authors checklist. */
const CHECKLIST = [
  {
    label: "A title",
    body: "specific enough that a reader scanning the archive knows what the paper claims.",
  },
  {
    label: "An abstract",
    body: "one self-contained paragraph: the problem, the approach, and what you found. It is the first (often the only) thing screening editors and archive readers see.",
  },
  {
    label: "Keywords",
    body: "a handful of terms (three to six is typical) under which the paper should be findable in the archive search.",
  },
  {
    label: "The manuscript, as a single PDF",
    body: "complete with figures, tables and references. There is no template requirement; there is a legibility one.",
  },
];

export function SubmissionChecklist() {
  return (
    <ul className="list-disc space-y-2 pl-5">
      {CHECKLIST.map((item) => (
        <li key={item.label}>
          <strong className="font-semibold text-ink">{item.label}</strong> — {item.body}
        </li>
      ))}
    </ul>
  );
}

/** Plain-words explanations of every status an author can see, in the order a manuscript
 * normally moves through them. Kept deliberately consistent with the sentences the signed-in
 * dashboards render from `src/lib/status.ts`, but written for a reader who is not signed in. */
const STATUSES = [
  { term: "Submitted", body: "Received and stamped with its tracking code. Waiting for an editor to begin screening. Nothing is expected from you." },
  { term: "Under screening", body: "An editor is reading the submission and deciding whether to send it to reviewers or to desk-reject it as out of scope." },
  { term: "In review", body: "With two independent reviewers under double-blind conditions. This is usually the longest stage; no action is needed from you." },
  { term: "Revision requested", body: "The editor has asked for changes — minor or major — before the manuscript can proceed. The reviewers' comments tell you what to address; the manuscript waits for your revised version." },
  { term: "Accepted", body: "Accepted for publication. Waiting to be scheduled into an issue; nothing further is needed from you." },
  { term: "Rejected", body: "Not accepted for publication, either at screening or after review. This is final for this manuscript." },
  { term: "Published", body: "Live in the public archive, full text readable by anyone, with the byline restored." },
  { term: "Withdrawn", body: "Removed from consideration at your request. This is final — a withdrawn manuscript is never reviewed or published." },
];

export function StatusGlossary() {
  return (
    <TermList>
      {STATUSES.map((status) => (
        <TermRow key={status.term} term={status.term}>
          {status.body}
        </TermRow>
      ))}
    </TermList>
  );
}
