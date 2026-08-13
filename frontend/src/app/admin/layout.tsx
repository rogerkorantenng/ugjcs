import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";
import { DemoBanner } from "@/components/layout/demo-banner";

/**
 * Same chrome as the editor layout, but gated on the administrator role in the layout
 * itself — `/admin` is not covered by the middleware's role-by-prefix map, so this check
 * is the route's only guard. An anonymous visitor is sent to sign in; a signed-in
 * account *without* the role goes to the public home page instead (mirroring the
 * middleware's role-mismatch redirect) — bouncing them to `/login?next=/admin` would
 * loop forever, because the login page sends live sessions straight back to `next`.
 * The backend re-checks the role on every `/admin/*` call regardless.
 */
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user) redirect("/login?next=/admin");
  if (!session.user.roles.includes("administrator")) redirect("/");
  return (
    <>
      <AppNav user={session.user} />
      <DemoBanner />
      <div className="mx-auto max-w-5xl px-4 py-8">{children}</div>
    </>
  );
}
