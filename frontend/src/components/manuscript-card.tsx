import Link from "next/link";
import { formatAuthors } from "@/lib/format";
import { TrackingChip } from "@/components/ui/tracking-chip";
import type { ArchivePaperOut } from "@/types/api";

export function PaperCard({ paper }: { paper: ArchivePaperOut }) {
  return (
    <Link
      href={`/papers/${paper.tracking_code}`}
      className="block rounded-[3px] border border-rule bg-white/70 p-5 transition-colors hover:border-teal/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
    >
      <TrackingChip code={paper.tracking_code} />
      <h3 className="mt-2 font-serif text-lg font-semibold text-ink">{paper.title}</h3>
      <p className="mt-1 text-sm text-ink/60">{formatAuthors(paper.author_names)}</p>
    </Link>
  );
}
