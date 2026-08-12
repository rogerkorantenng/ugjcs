"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { PdfDropzone } from "@/components/ui/file-drop";
import { uploadFormData } from "@/lib/upload";
import type { Manuscript, ProblemDetails } from "@/types/api";

/**
 * Multipart: `title`, `abstract`, `keywords`, `co_author_ids` and a required `file` PDF.
 * The `PdfDropzone` check below is a client-side courtesy, not the enforcement point — a
 * non-PDF or oversized upload still gets a 415/413 from the backend via `/api/manuscripts`,
 * relayed verbatim as a `ProblemAlert`.
 */
export default function SubmitPage() {
  const router = useRouter();
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError((current) => current ?? "Attach the manuscript PDF before submitting.");
      return;
    }
    const form = new FormData(event.currentTarget);
    const body = new FormData();
    body.set("title", String(form.get("title") ?? ""));
    body.set("abstract", String(form.get("abstract") ?? ""));
    body.set("keywords", String(form.get("keywords") ?? ""));
    body.set("co_author_ids", String(form.get("co_author_ids") ?? ""));
    body.set("file", file);

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
      const manuscript = outcome.data as Manuscript;
      router.push(`/author/${manuscript.tracking_code}`);
    } catch {
      setProblem({ type: "about:blank", title: "Could not reach the server", status: 0 });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">Submit a manuscript</h1>
      {problem && (
        <div className="mt-4">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate aria-busy={submitting}>
        <Input label="Title" name="title" required minLength={5} />
        <Textarea label="Abstract" name="abstract" required minLength={100} rows={6} />
        <Input label="Keywords (comma-separated)" name="keywords" required />
        <Input label="Co-author account ids (comma-separated, optional)" name="co_author_ids" />
        <PdfDropzone
          label="Manuscript PDF (max 10 MB)"
          file={file}
          onSelect={(selected, error) => {
            setFile(selected);
            setFileError(error);
          }}
          disabled={submitting}
        />
        {fileError && (
          <p role="alert" className="text-sm text-brick">
            {fileError}
          </p>
        )}
        <Button type="submit" isLoading={submitting}>
          {submitting ? `Uploading… ${progress}%` : "Submit manuscript"}
        </Button>
      </form>
    </>
  );
}
