"use client";
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import type { PersonLookup } from "@/types/api";

type LookupState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "found"; person: PersonLookup }
  | { status: "not-found"; email: string }
  | { status: "error" };

/**
 * Replaces the old "co-author account ids, comma-separated" free-text field — the one raw
 * database identifier this submission form used to demand. A submitter instead types an
 * email, resolves it against `GET /people/lookup` to a name they can confirm, and adds that
 * as a chip. `onChange` reports the resolved people list so the caller can post
 * `co_author_ids` from real, looked-up ids rather than parsing a comma-separated string.
 */
export function CoAuthorPicker({ people, onChange }: { people: PersonLookup[]; onChange: (people: PersonLookup[]) => void }) {
  const inputId = useId();
  const [email, setEmail] = useState("");
  const [lookup, setLookup] = useState<LookupState>({ status: "idle" });

  async function onLookup(event: FormEvent) {
    event.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setLookup({ status: "loading" });
    try {
      const response = await fetch(`/api/people/lookup?email=${encodeURIComponent(trimmed)}`);
      if (response.status === 404) {
        setLookup({ status: "not-found", email: trimmed });
        return;
      }
      if (!response.ok) {
        setLookup({ status: "error" });
        return;
      }
      const person = (await response.json()) as PersonLookup;
      setLookup({ status: "found", person });
    } catch {
      setLookup({ status: "error" });
    }
  }

  function addPerson(person: PersonLookup) {
    if (!people.some((existing) => existing.id === person.id)) onChange([...people, person]);
    setEmail("");
    setLookup({ status: "idle" });
  }

  function removePerson(id: string) {
    onChange(people.filter((person) => person.id !== id));
  }

  return (
    <div>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
        Co-authors (optional)
      </label>
      <p className="mb-1.5 text-xs text-ink/60">
        Enter a co-author&apos;s account email to look them up, then confirm and add them.
      </p>
      <form onSubmit={onLookup} className="flex gap-2">
        <input
          id={inputId}
          type="email"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            if (lookup.status !== "idle") setLookup({ status: "idle" });
          }}
          placeholder="co-author@example.com"
          className="w-full flex-1 rounded-[3px] border border-rule bg-surface px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(18,21,26,0.04)]
            transition-colors duration-150 placeholder:text-ink/35 hover:border-stamp/40
            focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:border-stamp/60"
        />
        <Button type="submit" variant="secondary" isLoading={lookup.status === "loading"} className="shrink-0">
          {lookup.status === "loading" ? "Looking up…" : "Look up"}
        </Button>
      </form>

      {lookup.status === "found" && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-[3px] border border-stamp/30 bg-stamp/[0.04] px-3 py-2">
          <p className="text-sm text-ink">
            <span className="font-medium">{lookup.person.full_name}</span>
            <span className="text-ink/60"> · {lookup.person.affiliation}</span>
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setLookup({ status: "idle" })}
              className="text-sm font-medium text-ink/60 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              Not them
            </button>
            <button
              type="button"
              onClick={() => addPerson(lookup.person)}
              className="text-sm font-semibold text-stamp hover:text-stamp-dark focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              Add as co-author
            </button>
          </div>
        </div>
      )}
      {lookup.status === "not-found" && (
        <p className="mt-2 text-sm text-seal">No account is registered with “{lookup.email}”.</p>
      )}
      {lookup.status === "error" && (
        <p className="mt-2 text-sm text-seal">Could not look up that email. Try again.</p>
      )}

      {people.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {people.map((person) => (
            <li
              key={person.id}
              className="flex items-center gap-2 rounded-full border border-stamp/30 bg-stamp/[0.05] py-1 pl-3 pr-1.5 text-sm text-ink"
            >
              <span>
                {person.full_name} <span className="text-ink/50">· {person.affiliation}</span>
              </span>
              <button
                type="button"
                onClick={() => removePerson(person.id)}
                aria-label={`Remove ${person.full_name} as a co-author`}
                className="grid h-5 w-5 place-items-center rounded-full text-ink/50 hover:bg-ink/10 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-1"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
