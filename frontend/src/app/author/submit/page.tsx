"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { PdfDropzone } from "@/components/ui/file-drop";
import { BackLink } from "@/components/ui/back-link";
import { CoAuthorPicker } from "@/components/co-author-picker";
import { SubmissionPreflight } from "@/components/anonymisation-report-card";
import { uploadFormData } from "@/lib/upload";
import { buildManuscriptFormData } from "@/lib/manuscript-form";
import type { PersonLookup, ProblemDetails } from "@/types/api";
import type { AnonymisationReport, SubmittedManuscript } from "@/types/scholarly";

/**
 * Multipart: `title`, `abstract`, `keywords`, `co_author_ids` and a required `file` PDF.
 * `co_author_ids` is built from `CoAuthorPicker`'s resolved people, never typed as raw
 * account ids. The `PdfDropzone` check below is a client-side courtesy, not the enforcement
 * point — a non-PDF or oversized upload still gets a 415/413 from the backend via
 * `/api/manuscripts`, relayed verbatim as a `ProblemAlert`.
 */
export default function SubmitPage() {
  const router = useRouter();
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [coAuthors, setCoAuthors] = useState<PersonLookup[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [preflight, setPreflight] = useState<{ report: AnonymisationReport; trackingCode: string } | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError((current) => current ?? "Attach the manuscript PDF before submitting.");
      return;
    }
    const body = buildManuscriptFormData(new FormData(event.currentTarget), coAuthors, file);

    setSubmitting(true);
    setProgress(0);
    setProblem(null);
    try {
      const outcome = await uploadFormData<unknown>("/api/manuscripts", body, setProgress);
      if (!outcome.ok) {
        const failure = (outcome.data as ProblemDetails | null) ??
          { type: "about:blank", title: "Could not submit the manuscript", status: outcome.status };
        setProblem(failure);
        return;
      }
      const manuscript = outcome.data as SubmittedManuscript;
      // Pause on the anonymisation report (when the backend attached one) before the
      // redirect; an older backend without the field redirects immediately, as before.
      if (manuscript.anonymisation_report) {
        setPreflight({ report: manuscript.anonymisation_report, trackingCode: manuscript.tracking_code });
        return;
      }
      router.push(`/author/${manuscript.tracking_code}?submitted=1`);
    } catch {
      setProblem({ type: "about:blank", title: "Could not reach the server", status: 0 });
    } finally {
      setSubmitting(false);
    }
  }

  if (preflight) {
    return (
      <SubmissionPreflight
        report={preflight.report}
        onContinue={() => router.push(`/author/${preflight.trackingCode}?submitted=1`)}
      />
    );
  }

  return (
    <>
      <BackLink href="/author" label="My submissions" />
      <h1 className="font-display-heading text-2xl font-semibold text-ink">Submit a manuscript</h1>
      <p className="mt-1 text-sm text-ink/60">
        Once submitted, the manuscript is accession-stamped and enters editorial screening. You can withdraw it any
        time before a decision is recorded.
      </p>
      {problem && (
        <div className="mt-4">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate aria-busy={submitting}>
        <Input label="Title" name="title" required minLength={5} hint="At least 5 characters." />
        <Textarea label="Abstract" name="abstract" required minLength={100} rows={6} hint="At least 100 characters." />
        <Input label="Keywords (comma-separated)" name="keywords" required />
        <CoAuthorPicker people={coAuthors} onChange={setCoAuthors} />
        <PdfDropzone
          label="Manuscript PDF (max 10 MB)"
          file={file}
          onSelect={(selected, error) => { setFile(selected); setFileError(error); }}
          disabled={submitting}
        />
        {fileError && <p role="alert" className="text-sm text-seal">{fileError}</p>}
        <Button type="submit" isLoading={submitting}>
          {submitting ? `Uploading… ${progress}%` : "Submit manuscript"}
        </Button>
      </form>
    </>
  );
}
