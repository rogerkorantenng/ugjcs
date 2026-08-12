import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";

export default async function AuthorLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user) redirect("/login?next=/author");
  return (
    <>
      <AppNav user={session.user} />
      <div className="mx-auto max-w-4xl px-4 py-8">{children}</div>
    </>
  );
}
