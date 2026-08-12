import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <main role="status" aria-live="polite" aria-busy="true" className="mx-auto max-w-3xl px-4 py-14">
      <span className="sr-only">Loading paper…</span>
      <Skeleton className="h-4 w-32" />
      <Skeleton className="mt-3 h-8 w-full" />
      <Skeleton className="mt-2 h-8 w-2/3" />
      <Skeleton className="mt-3 h-4 w-48" />
      <div className="mt-8 space-y-2 border-t border-rule pt-8">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </main>
  );
}
