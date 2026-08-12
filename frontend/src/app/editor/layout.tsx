import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";
import { DemoBanner } from "@/components/layout/demo-banner";

export default async function EditorLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user) redirect("/login?next=/editor");
  return (
    <>
      <AppNav user={session.user} />
      <DemoBanner />
      <div className="mx-auto max-w-4xl px-4 py-8">{children}</div>
    </>
  );
}
