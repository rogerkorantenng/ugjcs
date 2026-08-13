"use client";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { DemoBanner } from "@/components/layout/demo-banner";
import { roleHome } from "@/lib/role-home";
import type { ProblemDetails, SessionUser } from "@/types/api";

function LoginForm() {
  const router = useRouter();
  // No explicit destination means "take me to my desk" — which desk depends on the
  // roles the login response reveals, so the fallback is resolved after sign-in.
  const next = useSearchParams().get("next");
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  // Someone with a live session has no business at the sign-in form: send them straight
  // to their desk instead of asking for credentials they've already presented.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth/me")
      .then((response) => (response.ok ? response.json() : { user: null }))
      .then((data: { user: SessionUser | null }) => {
        if (!cancelled && data.user) router.replace(next ?? roleHome(data.user.roles));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [router, next]);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setProblem(null);
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setProblem((await response.json()) as ProblemDetails);
      return;
    }
    const { user } = (await response.json()) as { user: SessionUser };
    router.push(next ?? roleHome(user.roles));
    router.refresh();
  }

  return (
    <div className="animate-rise-in w-full max-w-sm border-2 border-stamp bg-paper p-8 shadow-[0_24px_60px_rgba(0,0,0,0.35)]">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">SDJ editorial portal</p>
      <h1 className="font-display-heading mt-2 text-2xl font-semibold text-ink">Sign in</h1>
      <p className="mt-1 text-sm text-ink/60">Enter your account credentials to continue.</p>
      {problem && <div className="mt-4"><ProblemAlert problem={problem} /></div>}
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate aria-busy={submitting}>
        <Input label="Email" name="email" type="email" required autoComplete="email" />
        <Input label="Password" name="password" type="password" required autoComplete="current-password" />
        <Button type="submit" isLoading={submitting} className="w-full">
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col bg-ink">
      <div className="mx-auto w-full max-w-5xl px-4 pt-8">
        <Link
          href="/"
          className="font-display-heading text-sm font-semibold tracking-tight text-paper focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          SDJ
        </Link>
      </div>
      <DemoBanner />
      <main className="flex flex-1 items-center justify-center px-4 py-16">
        {/* useSearchParams() forces a Suspense boundary in a statically-analysed route (Next 15) */}
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </main>
    </div>
  );
}
