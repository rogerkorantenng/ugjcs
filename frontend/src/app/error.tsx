"use client";
import { ErrorPanel } from "@/components/ui/error-panel";

export default function RootError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <ErrorPanel title="Something went wrong" message={error.message || "Please try again."} onRetry={reset} />
    </div>
  );
}
