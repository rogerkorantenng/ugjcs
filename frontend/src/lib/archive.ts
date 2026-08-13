import { backendFetch } from "@/lib/backend";
import type { ArchivePaperOut } from "@/types/api";
import type { ArchiveSearchHit } from "@/types/wave2";

const REVALIDATE_SECONDS = 300;

export function getPublishedPapers() {
  return backendFetch<ArchivePaperOut[]>("/archive", { next: { revalidate: REVALIDATE_SECONDS } });
}

export function getPaper(trackingCode: string) {
  return backendFetch<ArchivePaperOut>(`/archive/${trackingCode}`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
}

/** Hits may carry a `snippet` when the match came from indexed full text — see
 * `ArchiveSearchHit`; older backends that omit the field still parse fine. */
export function searchArchive(query: string) {
  return backendFetch<ArchiveSearchHit[]>(`/archive/search?q=${encodeURIComponent(query)}`, {
    next: { revalidate: 60 },
  });
}
