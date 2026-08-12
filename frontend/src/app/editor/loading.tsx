import { QueueTableSkeleton } from "@/components/skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <>
      <Skeleton className="h-7 w-48" />
      <QueueTableSkeleton label="Loading the screening queue…" />
    </>
  );
}
