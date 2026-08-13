import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage, ProseSection, TermRow, TermList } from "@/components/content/prose-page";

export const metadata: Metadata = {
  title: "For authors",
  description:
    "Submission guidelines for UGJCS: what to prepare, how anonymisation works, what your tracking code means, how to follow your manuscript's status, and how revision and withdrawal work.",
};

export default function ForAuthorsPage() {
  return (
    <ProsePage
      eyebrow="Author guidelines"
      title="For authors"
      lede="Submitting to UGJCS takes one form and one PDF. This page tells you what to prepare, what happens after you press submit, and how to read every status your manuscript can be in."
    >
      <ProseSection title="What to prepare">
        <p>A submission consists of four things, entered in a single form:</p>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="font-semibold text-ink">A title</strong> — specific enough that a reader
            scanning the archive knows what the paper claims.
          </li>
          <li>
            <strong className="font-semibold text-ink">An abstract</strong> — one self-contained
            paragraph: the problem, the approach, and what you found. It is the first (often the only)
            thing screening editors and archive readers see.
          </li>
          <li>
            <strong className="font-semibold text-ink">Keywords</strong> — a handful of terms
            (three to six is typical) under which the paper should be findable in the archive search.
          </li>
          <li>
            <strong className="font-semibold text-ink">The manuscript, as a single PDF</strong> —
            complete with figures, tables and references. There is no template requirement; there is a
            legibility one.
          </li>
        </ul>
        <p>
          <strong className="font-semibold text-ink">Co-authors</strong> are added by email address:
          type a co-author&rsquo;s registered email and the form resolves it to their name before you
          confirm. Each co-author therefore needs an account on this site before you submit. The person
          who submits is the corresponding author — the one who receives the decision and who alone can
          resubmit or withdraw the manuscript.
        </p>
      </ProseSection>

      <ProseSection title="Anonymisation — what you do, and what the system does">
        <p>
          You do not prepare a separate anonymised version. When your manuscript goes to review, the
          system automatically strips author-identifying metadata from the copy reviewers receive, and
          reviewers are never shown the byline — they see the paper, not the people.
        </p>
        <p>
          Reviewers do read the body of your PDF exactly as you wrote it, so be sensible about
          self-identification in the text itself: prefer &ldquo;prior work showed&rdquo; over
          &ldquo;in our earlier paper we showed&rdquo;, and leave acknowledgements and grant numbers
          for the accepted version.
        </p>
      </ProseSection>

      <ProseSection title="Your tracking code">
        <p>
          On submission your manuscript receives a tracking code such as{" "}
          <span className="font-mono text-sm text-ink">UGJCS-2026-0012</span> — the journal&rsquo;s
          initials, the year of submission, and a running number. It is the manuscript&rsquo;s permanent
          identity: it appears on your dashboard, on the manuscript&rsquo;s page, survives every
          revision, and becomes the paper&rsquo;s public address in the archive once published. Quote it
          in any correspondence about the submission.
        </p>
        <p>
          To follow progress, sign in and open your author dashboard: every manuscript is listed with
          its current status, and the manuscript&rsquo;s own page explains in a sentence what that
          status means and whether anything is expected from you. There is no separate tracking site
          and nothing to poll — the status you see is the live editorial state.
        </p>
      </ProseSection>

      <ProseSection title="What each status means">
        <TermList>
          <TermRow term="Submitted">
            Received and stamped with its tracking code. Waiting for an editor to begin screening.
            Nothing is expected from you.
          </TermRow>
          <TermRow term="Under screening">
            An editor is reading the submission and deciding whether to send it to reviewers or to
            desk-reject it as out of scope.
          </TermRow>
          <TermRow term="In review">
            With two independent reviewers under double-blind conditions. This is usually the longest
            stage; no action is needed from you.
          </TermRow>
          <TermRow term="Revision requested">
            The editor has asked for changes — minor or major — before the manuscript can proceed. The
            reviewers&rsquo; comments tell you what to address; the manuscript waits for your revised
            version.
          </TermRow>
          <TermRow term="Accepted">
            Accepted for publication. Waiting to be scheduled into an issue; nothing further is needed
            from you.
          </TermRow>
          <TermRow term="Rejected">
            Not accepted for publication, either at screening or after review. This is final for this
            manuscript.
          </TermRow>
          <TermRow term="Published">
            Live in the public archive, full text readable by anyone, with the byline restored.
          </TermRow>
          <TermRow term="Withdrawn">
            Removed from consideration at your request. This is final — a withdrawn manuscript is never
            reviewed or published.
          </TermRow>
        </TermList>
      </ProseSection>

      <ProseSection title="Revisions and resubmission">
        <p>
          A revision decision means the editors want to publish a better version of this paper. Revise
          the manuscript in light of the reviewers&rsquo; comments, then upload the new PDF from the
          manuscript&rsquo;s page. The resubmission keeps the same tracking code — it is the same
          manuscript, one version on.
        </p>
        <p>
          The revised version returns to the editor, who sends it out for a fresh round of review.
          Address every reviewer point, even the ones you disagree with — a reasoned rebuttal in the
          text is legitimate; silence is not. A minor revision is normally one round; a major revision
          is judged again from the start.
        </p>
      </ProseSection>

      <ProseSection title="Withdrawal">
        <p>
          The corresponding author may withdraw a manuscript at any point while it is under
          consideration — before screening, during review, or while a revision is pending — from the
          manuscript&rsquo;s page. Withdraw rather than abandon: it releases the reviewers and closes
          the record cleanly.
        </p>
        <p>
          Withdrawal is final. A withdrawn manuscript cannot be reinstated and its tracking code is not
          reused; if you later want the work considered again, submit it as a new manuscript. Once a
          paper is published it can no longer be withdrawn.
        </p>
      </ProseSection>

      <div className="mt-10 border-t border-rule pt-8 text-sm">
        <p className="text-ink/60">
          Ready to submit?{" "}
          <Link href="/login" className="font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp">
            Sign in
          </Link>{" "}
          and start from your author dashboard. For the process end to end, see{" "}
          <Link href="/about" className="font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp">
            how the journal works
          </Link>
          .
        </p>
      </div>
    </ProsePage>
  );
}
