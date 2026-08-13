import { TermRow, TermList } from "./prose-page";

/** The three parts of a complete UGJCS review, matching the fields of the review form the
 * assigned reviewer actually fills in — recommendation plus the two comment channels. */
const PARTS = [
  {
    term: "Recommendation",
    body: "One of four: accept, minor revision, major revision, or reject. This is your overall judgement; the written comments must support it.",
  },
  {
    term: "Comments to the authors",
    body: "The substance of the review, and the part the authors will read. Be specific and constructive: say what the paper claims, what holds, what does not, and what a revision would need to fix — numbered points make a revision checkable. Do not sign these comments or otherwise identify yourself.",
  },
  {
    term: "Comments to the editor",
    body: "Confidential, never shown to the authors. Use this for candour that does not belong in the author-facing text: suspicions about the work's provenance, a possible break in the blind, or how strongly you hold your recommendation.",
  },
];

export function ReviewParts() {
  return (
    <TermList>
      {PARTS.map((part) => (
        <TermRow key={part.term} term={part.term}>
          {part.body}
        </TermRow>
      ))}
    </TermList>
  );
}
