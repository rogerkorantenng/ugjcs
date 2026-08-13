"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { DocumentUrlOut } from "@/types/api";

type State =
  | { status: "loading" }
  | { status: "ready"; url: string }
  | { status: "expired" }
  | { status: "error"; message: string };

/**
 * Fetches a document's pre-signed URL from a same-origin BFF route (`?format=json`) and
 * tracks its ~5 minute expiry client-side. The URL is never lengthened or cached — this
 * hook re-fetches a fresh one only when the caller explicitly asks (mount, or "Reload
 * document"), which is the point of the pre-signed URL's short lifetime as a security
 * property, not an accident to work around.
 */
export function useDocumentUrl(jsonEndpoint: string) {
  const [state, setState] = useState<State>({ status: "loading" });
  const expiryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    if (expiryTimer.current) clearTimeout(expiryTimer.current);
    setState({ status: "loading" });
    try {
      const response = await fetch(jsonEndpoint);
      if (!response.ok) {
        setState({ status: "error", message: response.status === 404 ? "No document is on file." : "Could not load the document." });
        return;
      }
      const data = (await response.json()) as DocumentUrlOut;
      setState({ status: "ready", url: data.url });
      // Mark the preview expired a few seconds early — a viewer opened right at the edge of
      // the window should never be left staring at a frame the S3 URL has already rejected.
      const safetyMarginMs = 5_000;
      const timeoutMs = Math.max(0, data.expires_in_seconds * 1000 - safetyMarginMs);
      expiryTimer.current = setTimeout(() => setState({ status: "expired" }), timeoutMs);
    } catch {
      setState({ status: "error", message: "Could not reach the server." });
    }
  }, [jsonEndpoint]);

  useEffect(() => {
    load();
    return () => {
      if (expiryTimer.current) clearTimeout(expiryTimer.current);
    };
  }, [load]);

  return { state, reload: load };
}
