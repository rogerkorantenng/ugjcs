import { ManuscriptListSkeleton } from "@/components/skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <>
      <Skeleton className="h-7 w-56" />
      <ManuscriptListSkeleton withBadge={false} label="Loading your assignments…" />
    </>
  );
}
