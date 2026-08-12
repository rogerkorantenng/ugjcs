"use client";
import { ErrorPanel } from "@/components/ui/error-panel";

export default function PublicError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-24">
      <ErrorPanel
        title="We could not load the archive"
        message={error.message || "Please try again in a moment."}
        onRetry={reset}
      />
    </main>
  );
}
