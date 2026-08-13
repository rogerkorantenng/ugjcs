import "server-only";
import { env } from "@/lib/env";
import type { ProblemDetails } from "@/types/api";

export class ProblemDetailsError extends Error {
  constructor(
    public readonly problem: ProblemDetails,
    public readonly status: number,
  ) {
    super(problem.title);
    this.name = "ProblemDetailsError";
  }
}

async function toProblem(response: Response): Promise<ProblemDetails> {
  try {
    return (await response.json()) as ProblemDetails;
  } catch {
    return { type: "about:blank", title: response.statusText, status: response.status };
  }
}

/** For the public archive: never attaches a token, never reads the session. */
export async function backendFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${env.API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!response.ok) throw new ProblemDetailsError(await toProblem(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * `backendFetch` for text/plain bodies — the citation export endpoint answers with raw
 * BibTeX/RIS, not JSON. Same public posture: no token, no session; errors still arrive
 * as JSON problem details and are relayed as `ProblemDetailsError` exactly like above.
 */
export async function backendFetchText(path: string, init: RequestInit = {}): Promise<string> {
  const response = await fetch(`${env.API_BASE_URL}${path}`, init);
  if (!response.ok) throw new ProblemDetailsError(await toProblem(response), response.status);
  return response.text();
}
