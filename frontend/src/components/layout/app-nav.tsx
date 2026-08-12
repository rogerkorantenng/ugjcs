"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { SessionUser } from "@/types/api";

const LINKS: Record<string, { href: string; label: string }[]> = {
  author: [{ href: "/author", label: "My submissions" }, { href: "/author/submit", label: "Submit" }],
  reviewer: [{ href: "/reviewer", label: "My assignments" }],
  editor: [{ href: "/editor", label: "Screening queue" }],
  editor_in_chief: [{ href: "/editor", label: "Screening queue" }],
};

export function AppNav({ user }: { user: SessionUser }) {
  const router = useRouter();
  const links = user.roles.flatMap((role) => LINKS[role] ?? []);

  async function signOut() {
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
            className="text-sm font-medium text-paper/75 hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="flex items-center gap-4 text-sm text-paper/75">
        {/* `SessionUser` has no `name` — `GET /auth/me` (`ActorOut`) serialises only
            `{id, roles}`; `email` is the one human-readable field the session carries. */}
        <span className="font-mono text-xs">{user.email}</span>
        <button onClick={signOut} className="font-medium text-amber hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber">
          Sign out
        </button>
      </div>
    </nav>
  );
}
