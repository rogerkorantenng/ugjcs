"use client";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { QueueTableSkeleton } from "@/components/skeletons";
import { QueueSection, QUEUE_SECTIONS } from "@/components/queue-section";
import { Tour } from "@/components/tour/tour";
import { EDITOR_TOUR } from "@/components/tour/steps";
import type { Manuscript } from "@/types/api";

export default function EditorialQueue() {
  const { data, error, isLoading } = useApi<Manuscript[]>("/api/editorial/queue");

  return (
    <>
      <Tour steps={EDITOR_TOUR.steps} storageKey={EDITOR_TOUR.storageKey} />
      <h1 data-tour="editor-welcome" className="font-display-heading text-2xl font-semibold text-ink">Editorial queue</h1>

      {isLoading && <QueueTableSkeleton label="Loading the queue…" />}

      {error && (
        <div className="mt-4">
          <ProblemAlert
            problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
          />
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState
          title="No manuscripts need editorial attention"
          hint="New submissions and manuscripts moving through review will appear here."
        />
      )}

      {data && data.length > 0 && (
        <div data-tour="editor-queue" className="mt-4 space-y-8">
          {QUEUE_SECTIONS.map((section) => {
            const manuscripts = data.filter((m) => m.status === section.status);
            if (manuscripts.length === 0) return null;
            return <QueueSection key={section.status} section={section} manuscripts={manuscripts} />;
          })}
        </div>
      )}
    </>
  );
}
