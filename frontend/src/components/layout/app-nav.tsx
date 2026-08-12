"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/spinner";
import type { SessionUser } from "@/types/api";

const LINKS: Record<string, { href: string; label: string }[]> = {
  author: [{ href: "/author", label: "My submissions" }, { href: "/author/submit", label: "Submit" }],
  reviewer: [{ href: "/reviewer", label: "My assignments" }],
  editor: [{ href: "/editor", label: "Screening queue" }],
  editor_in_chief: [{ href: "/editor", label: "Screening queue" }],
};

export function AppNav({ user }: { user: SessionUser }) {
  const router = useRouter();
  const pathname = usePathname();
  const [signingOut, setSigningOut] = useState(false);
  const links = user.roles.flatMap((role) => LINKS[role] ?? []);
  // The longest matching href wins, so `/author/submit` highlights "Submit" rather than
  // also lighting up "My submissions" for the shared `/author` prefix.
  const activeHref = [...links]
    .sort((a, b) => b.href.length - a.href.length)
    .find((link) => pathname === link.href || pathname.startsWith(`${link.href}/`))?.href;

  async function signOut() {
    setSigningOut(true);
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <nav aria-label="Account navigation" className="flex items-center justify-between border-b border-amber/40 bg-ink px-4 py-4 text-paper">
      <div className="flex items-center gap-6">
        <span className="font-serif text-sm font-semibold tracking-tight">UGJCS</span>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            aria-current={link.href === activeHref ? "page" : undefined}
            className={`text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber ${
              link.href === activeHref ? "text-amber" : "text-paper/75 hover:text-paper"
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="flex items-center gap-4 text-sm text-paper/75">
        {/* `SessionUser` has no `name` — `GET /auth/me` (`ActorOut`) serialises only
            `{id, roles}`; `email` is the one human-readable field the session carries. */}
        <span className="font-mono text-xs">{user.email}</span>
        <button
          onClick={signOut}
          disabled={signingOut}
          aria-busy={signingOut}
          className="inline-flex items-center gap-1.5 font-medium text-amber hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber disabled:cursor-not-allowed disabled:opacity-60"
        >
          {signingOut && <Spinner className="h-3.5 w-3.5" />}
          {signingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>
    </nav>
  );
}
