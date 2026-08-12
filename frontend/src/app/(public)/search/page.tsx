import { searchArchive } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonClasses } from "@/components/ui/button";

export const metadata = { title: "Search" };

interface SearchParams { q?: string }

export default async function SearchPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { q = "" } = await searchParams;
  const results = q ? await searchArchive(q) : [];

  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <h1 className="font-serif text-2xl font-semibold text-ink">Search</h1>
      <form className="mt-6 flex flex-col gap-2 sm:flex-row" role="search">
        <div className="flex-1">
          <label htmlFor="q" className="sr-only">Search papers</label>
          <input
            id="q"
            name="q"
            defaultValue={q}
            placeholder="Title, abstract or keyword"
            className="w-full rounded-[3px] border border-rule bg-white px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
          />
        </div>
        <button type="submit" className={buttonClasses("primary", "shrink-0")}>Search</button>
      </form>
      {!q && (
        <p className="mt-8 text-sm text-ink/60">Enter a title, abstract or keyword to search the archive.</p>
      )}
      {results.length > 0 && (
        <div className="mt-8 grid gap-4">
          {results.map((paper) => (
            <PaperCard key={paper.tracking_code} paper={paper} />
          ))}
        </div>
      )}
      {q && results.length === 0 && (
        <EmptyState title={`No papers matched “${q}”`} hint="Try a different title or keyword." />
      )}
      {/*
        No pagination control: `/archive/search` returns a flat, unbounded array. A
        `limit`/`offset` UI can be added the day the backend adds the query parameters.
      */}
    </main>
  );
}
