"use client";
import { ErrorPanel } from "@/components/ui/error-panel";

export default function AuthorError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <ErrorPanel title="Something went wrong" message={error.message || "Please try again."} onRetry={reset} />
    </div>
  );
}
