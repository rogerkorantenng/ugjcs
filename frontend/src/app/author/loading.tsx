import { ManuscriptListSkeleton } from "@/components/skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <>
      <Skeleton className="h-7 w-48" />
      <ManuscriptListSkeleton label="Loading your submissions…" />
    </>
  );
}
