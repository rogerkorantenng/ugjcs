import type { PersonLookup } from "@/types/api";

/**
 * Collects the submission form's fields into the multipart body `/api/manuscripts`
 * expects. `co_author_ids` comes from the picker's resolved people, never raw typed ids.
 */
export function buildManuscriptFormData(form: FormData, coAuthors: PersonLookup[], file: File): FormData {
  const body = new FormData();
  body.set("title", String(form.get("title") ?? ""));
  body.set("abstract", String(form.get("abstract") ?? ""));
  body.set("keywords", String(form.get("keywords") ?? ""));
  body.set("co_author_ids", coAuthors.map((person) => person.id).join(","));
  body.set("file", file);
  return body;
}
