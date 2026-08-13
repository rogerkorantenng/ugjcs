"use client";
import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/spinner";
import { TOUR_START_EVENT } from "@/components/tour/tour";
import type { SessionUser } from "@/types/api";

// Exactly the routes that mount a `<Tour>`; the "Show me around" trigger only renders
// where dispatching the start event will actually reach a listener.
const TOUR_ROOTS = new Set(["/author", "/reviewer", "/editor"]);

const ROLE_LABELS: Record<string, string> = {
  author: "Author",
  reviewer: "Reviewer",
  editor: "Editor",
  editor_in_chief: "Editor-in-Chief",
  administrator: "Administrator",
};

/** The masthead's right-hand session cluster: the tour trigger, the signed-in reader's
 * role chip and email, and sign-out. Extracted from `AppNav` unchanged, so the nav
 * itself stays a list of links. */
export function AppNavSession({ user }: { user: SessionUser }) {
  const router = useRouter();
  const pathname = usePathname();
  const [signingOut, setSigningOut] = useState(false);
  const primaryRole = user.roles.includes("editor_in_chief") ? "editor_in_chief" : user.roles[0];

  async function signOut() {
    setSigningOut(true);
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="flex items-center gap-4 text-sm text-paper/75">
      {TOUR_ROOTS.has(pathname) && (
        <button
          onClick={() => window.dispatchEvent(new Event(TOUR_START_EVENT))}
          className="font-medium text-paper/60 transition-colors hover:text-paper focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          Show me around
        </button>
      )}
      <span className="hidden items-center gap-2 sm:flex">
        {primaryRole && (
          <span className="rounded-full border border-ug-gold/60 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ug-gold">
            {ROLE_LABELS[primaryRole] ?? primaryRole}
          </span>
        )}
        <span className="font-mono text-xs">{user.email}</span>
      </span>
      <button
        onClick={signOut}
        disabled={signingOut}
        aria-busy={signingOut}
        className="inline-flex items-center gap-1.5 font-medium text-paper/85 transition-colors hover:text-paper focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {signingOut && <Spinner className="h-3.5 w-3.5" />}
        {signingOut ? "Signing out…" : "Sign out"}
      </button>
    </div>
  );
}
