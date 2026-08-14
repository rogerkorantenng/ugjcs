import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";
import { DemoBanner } from "@/components/layout/demo-banner";
import { CreditFooter } from "@/components/layout/credit-footer";

export default async function AuthorLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user) redirect("/login?next=/author");
  return (
    <>
      <AppNav user={session.user} />
      <DemoBanner />
      <div className="mx-auto max-w-4xl px-4 py-8">{children}</div>
      <CreditFooter />
    </>
  );
}
