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
  if (!response.ok) throw new ClientApiError((await response.json()) as ProblemDetails);
  return (await response.json()) as T;
}

export function useApi<T>(url: string | null, config?: SWRConfiguration) {
  return useSWR<T>(url, fetcher, config);
}
