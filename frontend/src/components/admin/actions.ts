import type { ProblemDetails } from "@/types/api";

/**
 * One shape for every admin console mutation — `POST /api/admin/accounts/{id}/{path}`.
 * Returns `null` on success, or the `ProblemDetails` to show beside the row on failure.
 */
export async function postAccountAction(id: string, path: string, body: unknown): Promise<ProblemDetails | null> {
  const response = await fetch(`/api/admin/accounts/${id}/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (response.ok) return null;
  const detail = (await response.json().catch(() => null)) as ProblemDetails | null;
  return detail ?? { type: "about:blank", title: "The change could not be saved", status: response.status };
}
