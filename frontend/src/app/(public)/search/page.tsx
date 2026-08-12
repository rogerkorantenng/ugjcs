import { searchArchive } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";

export const metadata = { title: "Search" };

interface SearchParams { q?: string }

export default async function SearchPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { q = "" } = await searchParams;
  const results = q ? await searchArchive(q) : [];

  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <h1 className="font-serif text-2xl font-semibold text-ink">Search</h1>
      <form className="mt-6" role="search">
        <label htmlFor="q" className="sr-only">Search papers</label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          placeholder="Title, abstract or keyword"
          className="w-full rounded-[3px] border border-rule bg-white px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
        />
      </form>
      <div className="mt-8 grid gap-4">
        {results.map((paper) => (
          <PaperCard key={paper.tracking_code} paper={paper} />
        ))}
      </div>
      {q && results.length === 0 && (
        <p className="mt-8 text-sm text-ink/60">No papers matched &ldquo;{q}&rdquo;.</p>
      )}
      {/*
        No pagination control: `/archive/search` returns a flat, unbounded array. A
        `limit`/`offset` UI can be added the day the backend adds the query parameters.
      */}
    </main>
  );
}
