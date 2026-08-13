import Link from "next/link";
import { formatAuthors } from "@/lib/format";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { cardLinkClasses } from "@/components/ui/card";
import type { ArchivePaperOut } from "@/types/api";

export function PaperCard({ paper }: { paper: ArchivePaperOut }) {
  return (
    <Link href={`/papers/${paper.tracking_code}`} className={cardLinkClasses("group", "p-5")}>
      <TrackingChip code={paper.tracking_code} />
      <h3 className="font-display-heading mt-2 text-lg font-semibold text-ink group-hover:text-stamp">{paper.title}</h3>
      <p className="mt-1 text-sm text-ink/60">{formatAuthors(paper.author_names)}</p>
      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink/70">{paper.abstract}</p>
      {paper.keywords.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {paper.keywords.slice(0, 4).map((keyword) => (
            <li key={keyword} className="rounded-full border border-rule px-2 py-0.5 text-[11px] uppercase tracking-wide text-ink/50">
              {keyword}
            </li>
          ))}
        </ul>
      )}
    </Link>
  );
}
