"use client";
import useSWR, { type SWRConfiguration } from "swr";
import type { ProblemDetails } from "@/types/api";

export class ClientApiError extends Error {
  constructor(public readonly problem: ProblemDetails) {
    super(problem.title);
  }
}

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const problem = (await response.json()) as ProblemDetails;
    // A 401 here means the session is dead — expired, or (after the demo database is
    // reseeded) pointing at an account that no longer exists. The BFF has already
    // cleared the cookie by the time this response arrives; sending the reader to
    // sign-in beats leaving them on a dashboard that can load nothing.
    if (problem.status === 401 && typeof window !== "undefined") {
      window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    }
    throw new ClientApiError(problem);
  }
  return (await response.json()) as T;
}

export function useApi<T>(url: string | null, config?: SWRConfiguration) {
  return useSWR<T>(url, fetcher, config);
}
