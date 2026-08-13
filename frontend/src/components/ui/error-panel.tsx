"use client";
import { Button } from "./button";

/**
 * The one shape every `error.tsx` boundary renders through — a caught render error is still
 * a visible, readable message with a way forward, not a blank screen. Distinct from
 * `ProblemAlert`: that one renders a `ProblemDetails` the server already produced; this one
 * renders a thrown `Error` a boundary caught, and offers `reset()` where the caller has one.
 */
export function ErrorPanel({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="mx-auto max-w-md border-l-2 border-seal bg-seal/5 px-6 py-8 text-center">
      <p className="font-serif text-lg font-semibold text-seal">{title}</p>
      {message && <p className="mt-2 text-sm text-ink/70">{message}</p>}
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
