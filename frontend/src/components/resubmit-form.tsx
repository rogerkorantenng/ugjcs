"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { PdfDropzone } from "@/components/ui/file-drop";
import { uploadFormData } from "@/lib/upload";
import type { ProblemDetails } from "@/types/api";

/**
 * The corresponding author's only route back into the workflow from
 * `revision_requested` — the caller (`author/[trackingCode]/page.tsx`) is responsible for
 * rendering this only in that status; the backend re-checks both the status transition and
 * ownership (`Action.RESUBMIT`) regardless of what the UI shows.
 */
export function ResubmitForm({ trackingCode, onResubmitted }: { trackingCode: string; onResubmitted: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError((current) => current ?? "Attach the revised manuscript PDF before resubmitting.");
      return;
    }
    const form = new FormData(event.currentTarget);
    const body = new FormData();
    body.set("response_to_reviewers", String(form.get("response_to_reviewers") ?? ""));
    body.set("file", file);

    setSubmitting(true);
    setProgress(0);
    setProblem(null);
    try {
      const outcome = await uploadFormData<unknown>(`/api/manuscripts/${trackingCode}/resubmit`, body, setProgress);
      if (!outcome.ok) {
        const failure = (outcome.data as ProblemDetails | null) ??
          { type: "about:blank", title: "Could not resubmit the manuscript", status: outcome.status };
        setProblem(failure);
        return;
      }
      setFile(null);
      onResubmitted();
    } catch {
      setProblem({ type: "about:blank", title: "Could not reach the server", status: 0 });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 space-y-4" aria-label="Resubmit revised manuscript" aria-busy={submitting}>
      {problem && <ProblemAlert problem={problem} />}
      <PdfDropzone
        label="Revised manuscript PDF (max 10 MB)"
        file={file}
        onSelect={(selected, error) => {
          setFile(selected);
          setFileError(error);
        }}
        disabled={submitting}
      />
      {fileError && (
        <p role="alert" className="text-sm text-seal">
          {fileError}
        </p>
      )}
      <Textarea
        label="Response to reviewers"
        name="response_to_reviewers"
        required
        minLength={20}
        hint="At least 20 characters — explain what changed since the last version."
      />
      <Button type="submit" isLoading={submitting}>
        {submitting ? `Uploading… ${progress}%` : "Resubmit manuscript"}
      </Button>
    </form>
  );
}
