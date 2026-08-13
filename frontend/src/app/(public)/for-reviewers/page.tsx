import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage, ProseSection } from "@/components/content/prose-page";
import { ReviewParts } from "@/components/content/review-parts";

export const metadata: Metadata = {
  title: "For reviewers",
  description:
    "Reviewer guidance for UGJCS: the double-blind rules, what a review contains, how the conflict-of-interest check works, and what timeliness the journal expects.",
};

const link = "font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp";

export default function ForReviewersPage() {
  return (
    <ProsePage
      eyebrow="Reviewer guidelines"
      title="For reviewers"
      lede="Reviewers are the journal's quality control. This page sets out the double-blind rules you review under, what a complete review contains, how conflicts of interest are handled, and how quickly we ask you to work."
    >
      <ProseSection title="Double-blind, in both directions">
        <p>
          UGJCS reviews are double-blind. You never see the authors&rsquo; names: the copy you receive has the
          byline withheld and author-identifying metadata stripped from the file automatically. The authors, in
          turn, never learn who reviewed them — your identity is known only to the editors.
        </p>
        <p>
          The blind only works if you respect it. Do not try to identify the authors — no searching for
          distinctive phrases, no tracing the citation trail to guess a research group. If the manuscript
          accidentally gives its authors away, say so in your confidential comments to the editor, and continue
          only if you can still judge the work impartially.
        </p>
        <p>Treat the manuscript as confidential: do not share it, cite it, or use its ideas before it is published.</p>
      </ProseSection>

      <ProseSection title="What a review contains">
        <p>A complete review has three parts, entered in one form:</p>
        <ReviewParts />
        <p>
          Review the paper in front of you, not the paper you would have written. A recommendation to reject
          needs the same specificity as one to accept.
        </p>
      </ProseSection>

      <ProseSection title="Conflicts of interest">
        <p>
          The system screens for conflicts before you are ever assigned: when an editor picks reviewers,
          candidates who share an affiliation with any of the manuscript&rsquo;s authors, or who have a recent
          co-authorship with one of them, are marked ineligible — with the reason visible to the editor — and
          cannot be assigned. You will not be asked to review a colleague or a recent collaborator.
        </p>
        <p>
          No automatic check catches everything. If, on reading a manuscript, you recognise a conflict the system
          could not see — a former student&rsquo;s work, a project you advised on, a direct competitor to your
          own unpublished results — declare it in your comments to the editor instead of reviewing.
        </p>
      </ProseSection>

      <ProseSection title="Timeliness">
        <p>
          Aim to submit your review within three weeks of assignment. A manuscript cannot move until both reviews
          are in, so a late review holds another researcher&rsquo;s work in limbo — the author sees only
          &ldquo;in review&rdquo;, for as long as the slowest reviewer takes.
        </p>
        <p>
          If you cannot meet that, say so to the editorial office early — a prompt &ldquo;no&rdquo; or a
          realistic date is genuinely useful; silence is not. Assignments you accept appear on your reviewer
          dashboard when you sign in, so what is on your desk is never a matter of memory.
        </p>
      </ProseSection>

      <div className="mt-10 border-t border-rule pt-8 text-sm">
        <p className="text-ink/60">
          Assigned a manuscript? <Link href="/login" className={link}>Sign in</Link> to see it on your reviewer
          dashboard. For the editorial process end to end, see{" "}
          <Link href="/about" className={link}>how the journal works</Link>.
        </p>
      </div>
    </ProsePage>
  );
}
