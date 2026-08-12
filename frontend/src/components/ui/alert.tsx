import type { ProblemDetails } from "@/types/api";

export function ProblemAlert({ problem }: { problem: ProblemDetails }) {
  return (
    <div role="alert" className="flex gap-3 border-l-2 border-brick bg-brick/5 px-4 py-3">
      <span aria-hidden="true" className="mt-0.5 text-brick">⚠</span>
      <div>
        <p className="font-semibold text-brick">{problem.title}</p>
        {problem.detail && <p className="mt-1 text-sm text-ink/70">{problem.detail}</p>}
      </div>
    </div>
  );
}
