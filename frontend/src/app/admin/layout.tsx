import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";
import { DemoBanner } from "@/components/layout/demo-banner";

/**
 * Same chrome as the editor layout, but gated on the administrator role in the layout
 * itself — `/admin` is not covered by the middleware's role-by-prefix map, so this check
 * is the route's only guard. Anyone else is sent to sign in, exactly like an anonymous
 * visitor; the backend re-checks the role on every `/admin/*` call regardless.
 */
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user || !session.user.roles.includes("administrator")) redirect("/login?next=/admin");
  return (
    <>
      <AppNav user={session.user} />
      <DemoBanner />
      <div className="mx-auto max-w-5xl px-4 py-8">{children}</div>
    </>
  );
}
