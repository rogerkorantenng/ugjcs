"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import type { Manuscript, ProblemDetails } from "@/types/api";

export default function SubmitPage() {
  const router = useRouter();
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const keywords = String(form.get("keywords") ?? "").split(",").map((k) => k.trim()).filter(Boolean);
    const coAuthorIds = String(form.get("co_author_ids") ?? "").split(",").map((id) => id.trim()).filter(Boolean);
    setSubmitting(true);
    setProblem(null);
    const response = await fetch("/api/manuscripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: form.get("title"),
        abstract: form.get("abstract"),
        keywords,
        co_author_ids: coAuthorIds,
      }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setProblem((await response.json()) as ProblemDetails);
      return;
    }
    const manuscript = (await response.json()) as Manuscript;
    router.push(`/author/${manuscript.tracking_code}`);
  }

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">Submit a manuscript</h1>
      {/*
        No file field: Plan 4's `POST /manuscripts` takes a JSON body — `title`, `abstract`,
        `keywords`, `co_author_ids` — and nothing else. There is no manuscript file storage
        anywhere in the domain built by Plans 1–4.
      */}
      {problem && <div className="mt-4"><ProblemAlert problem={problem} /></div>}
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Input label="Title" name="title" required minLength={5} />
        <div>
          <label htmlFor="abstract" className="mb-1.5 block text-sm font-medium text-ink">Abstract</label>
          <textarea
            id="abstract"
            name="abstract"
            required
            minLength={100}
            rows={6}
            className="w-full rounded-[3px] border border-rule bg-white px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
          />
        </div>
        <Input label="Keywords (comma-separated)" name="keywords" required />
        <Input label="Co-author account ids (comma-separated, optional)" name="co_author_ids" />
        <Button type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit manuscript"}</Button>
      </form>
    </>
  );
}
