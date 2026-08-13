import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage, ProseSection } from "@/components/content/prose-page";
import { EditorialProcess, DecisionGlossary } from "@/components/content/editorial-process";

export const metadata: Metadata = {
  title: "About the portal",
  description:
    "What the SDJ Editorial Portal does for the Science and Development Journal (CBAS, University of Ghana), and how a manuscript moves through its double-blind editorial process, step by step.",
};

const link = "font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp";

export default function AboutPage() {
  return (
    <ProsePage
      eyebrow="About the portal"
      title="About the SDJ Editorial Portal"
      lede="The Science and Development Journal, published by the College of Basic and Applied Sciences at the University of Ghana, has long run its editorial work over email and shared drives. This portal moves that work into one system: every manuscript follows the same visible route — screening, two independent double-blind reviews, and an editorial decision."
    >
      <ProseSection title="What the portal does">
        <p>
          The portal carries a manuscript through the journal&rsquo;s whole editorial life. Authors submit a
          title, abstract, keywords and a PDF in one form and receive a tracking code; editors screen submissions
          and assign reviewers; reviewers read an automatically anonymised copy and return their reports; and
          decisions, revisions and publication are all recorded against the same manuscript record.
        </p>
        <p>
          What used to be an inbox thread — attachments forwarded to reviewers, decisions typed out by hand,
          statuses answered on request — becomes a single live record. The author sees the manuscript&rsquo;s
          status at any moment, the editor sees the whole queue, and nothing depends on anyone&rsquo;s memory of
          who was sent what.
        </p>
      </ProseSection>

      <ProseSection title="How a manuscript moves through the portal">
        <p>
          The process is deliberately simple, and every stage of it is visible to the author through the
          manuscript&rsquo;s status. From submission to decision:
        </p>
        <EditorialProcess />
      </ProseSection>

      <ProseSection title="What each decision means">
        <DecisionGlossary />
      </ProseSection>

      <ProseSection title="Who it is for">
        <p>
          Three groups of people work here. Authors — researchers submitting to the Science and Development
          Journal — use the portal to submit, follow their manuscript&rsquo;s status, resubmit revisions and
          read decisions. Reviewers receive their assignments and file their reports through it. And the
          journal&rsquo;s editors run screening, reviewer selection, decisions and publishing from a single
          queue. Published papers land in an open archive that anyone can read without an account.
        </p>
      </ProseSection>

      <ProseSection title="A note on this site">
        <p>
          This portal is a student capstone project, built as coursework for an Advanced Software Engineering
          exam. The editorial workflow described on this page — submission, screening, double-blind review,
          decisions, resubmission and publication — is real and fully working in this system, but the portal is
          not the Science and Development Journal&rsquo;s official system and not an official University of
          Ghana service, and the papers in the archive are demonstration content.
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
