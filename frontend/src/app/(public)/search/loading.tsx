import { ArchiveListSkeleton } from "@/components/skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="mt-6 h-10 w-full" />
      <ArchiveListSkeleton count={3} label="Searching the archive…" />
    </main>
  );
}
