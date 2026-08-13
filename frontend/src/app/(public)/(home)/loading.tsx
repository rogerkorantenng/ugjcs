import { ArchiveListSkeleton } from "@/components/skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <Skeleton className="h-3 w-56" />
      <Skeleton className="mt-3 h-9 w-full max-w-xl" />
      <Skeleton className="mt-2 h-4 w-2/3 max-w-md" />
      <Skeleton className="mt-6 h-4 w-40" />
      <div className="mt-14">
        <Skeleton className="h-5 w-48" />
        <ArchiveListSkeleton label="Loading recently published papers…" />
      </div>
    </main>
  );
}
