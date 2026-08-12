import { backendFetch } from "@/lib/backend";
import type { ArchivePaperOut } from "@/types/api";

const REVALIDATE_SECONDS = 300;

export function getPublishedPapers() {
  return backendFetch<ArchivePaperOut[]>("/archive", { next: { revalidate: REVALIDATE_SECONDS } });
}

export function getPaper(trackingCode: string) {
  return backendFetch<ArchivePaperOut>(`/archive/${trackingCode}`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
}

export function searchArchive(query: string) {
  return backendFetch<ArchivePaperOut[]>(`/archive/search?q=${encodeURIComponent(query)}`, {
    next: { revalidate: 60 },
  });
}
