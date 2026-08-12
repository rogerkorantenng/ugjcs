import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";

export default async function ReviewerLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user) redirect("/login?next=/reviewer");
  return (
    <>
      <AppNav user={session.user} />
      <div className="mx-auto max-w-4xl px-4 py-8">{children}</div>
    </>
  );
}
