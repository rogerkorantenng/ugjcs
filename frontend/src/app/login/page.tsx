"use client";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { DemoBanner } from "@/components/layout/demo-banner";
import { DemoAccountPicker } from "@/components/auth/demo-account-picker";
import { roleHome } from "@/lib/role-home";
import type { ProblemDetails, SessionUser } from "@/types/api";

type Mode = "sign-in" | "sign-up";

function AuthPanel() {
  const router = useRouter();
  // No explicit destination means "take me to my desk" — which desk depends on the
  // roles the login response reveals, so the fallback is resolved after sign-in.
  const next = useSearchParams().get("next");
  const [mode, setMode] = useState<Mode>("sign-in");
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Controlled so the demo-account chips can write into it; the password never is.
  const [email, setEmail] = useState("");
  const passwordRef = useRef<HTMLInputElement>(null);

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

  function switchMode(target: Mode) {
    setMode(target);
    setProblem(null);
    // The form remounts on `key={mode}`, clearing every uncontrolled field; the email is
    // controlled now, so it has to be cleared by hand to keep that same clean-slate rule.
    setEmail("");
  }

  /** Fill the address, then put the cursor where the reader still has work to do. */
  function pickDemoAccount(address: string) {
    setEmail(address);
    setProblem(null);
    passwordRef.current?.focus();
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setProblem(null);
    const form = new FormData(event.currentTarget);
    const endpoint = mode === "sign-in" ? "/api/auth/login" : "/api/auth/register";
    const payload =
      mode === "sign-in"
        ? { email: form.get("email"), password: form.get("password") }
        : {
            email: form.get("email"),
            password: form.get("password"),
            full_name: form.get("full_name"),
            affiliation: form.get("affiliation"),
          };
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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

  const signingIn = mode === "sign-in";

  return (
    <div className="w-full max-w-sm">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">SDJ editorial portal</p>
      <h1 className="font-display-heading mt-2 text-2xl font-semibold text-ink" aria-live="polite">
        {signingIn ? "Sign in" : "Create your author account"}
      </h1>
      <p className="mt-1 text-sm text-ink/60">
        {signingIn
          ? "Enter your account credentials to continue."
          : "Authors register themselves; reviewer and editor accounts are appointed by the editorial office."}
      </p>
      {problem && <div className="mt-4"><ProblemAlert problem={problem} /></div>}
      {signingIn && <DemoAccountPicker selected={email} onPick={pickDemoAccount} />}
      {/* Keyed on mode so the panel re-enters with the rise animation on each switch —
          a full remount also clears field state, so a half-typed password never carries
          over from one form into the other. `animate-rise-in` respects reduced motion. */}
      <form key={mode} onSubmit={onSubmit} className="animate-rise-in mt-6 space-y-4" noValidate aria-busy={submitting}>
        {!signingIn && (
          <>
            <Input label="Full name" name="full_name" required autoComplete="name" />
            <Input
              label="Affiliation"
              name="affiliation"
              required
              autoComplete="organization"
              hint="Your institution, e.g. University of Ghana"
            />
          </>
        )}
        <Input
          label="Email"
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Input
          ref={passwordRef}
          label="Password"
          name="password"
          type="password"
          required
          autoComplete={signingIn ? "current-password" : "new-password"}
          hint={signingIn ? undefined : "At least 12 characters — length beats symbols."}
        />
        <Button type="submit" isLoading={submitting} className="w-full">
          {submitting
            ? signingIn ? "Signing in…" : "Creating account…"
            : signingIn ? "Sign in" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 border-t border-rule pt-4 text-sm text-ink/70">
        {signingIn ? "New to the journal?" : "Already have an account?"}{" "}
        <button
          type="button"
          onClick={() => switchMode(signingIn ? "sign-up" : "sign-in")}
          className="font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          {signingIn ? "Sign up as an author" : "Sign in"}
        </button>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      {/* Above the fold, not under it: this is the first thing anyone landing on the portal
          reads, and since `/` now lands here it is the notice for the whole site. */}
      <DemoBanner />
      <div className="grid flex-1 lg:grid-cols-2">
        {/* The campus, filling the left half on wide screens and a banner strip on small
            ones. Decorative: the empty alt keeps screen readers on the form. No
            `lg:min-h-screen`: the grid is already `flex-1` inside a `min-h-screen` column,
            so a full viewport here would push the page past the fold by the banner's height. */}
        <div className="relative h-44 sm:h-56 lg:h-auto">
          <Image
            src="/legon-campus.jpg"
            alt=""
            fill
            priority
            sizes="(min-width: 1024px) 50vw, 100vw"
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-ug-blue/80 via-ug-blue/20 to-transparent" aria-hidden="true" />
          <div className="absolute bottom-0 left-0 right-0 p-6 text-paper">
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-ug-gold">
              College of Basic and Applied Sciences · University of Ghana
            </p>
            <p className="font-display-heading mt-1 text-lg font-semibold leading-tight sm:text-xl">
              Science and Development Journal
            </p>
          </div>
        </div>

        <div className="flex flex-col">
          <div className="flex items-center justify-between px-6 pt-6 lg:px-10">
            <Link
              href="/search"
              className="font-display-heading text-sm font-semibold tracking-tight text-ink focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              SDJ
            </Link>
            <Link href="/search" className="text-sm font-medium text-ink/60 hover:text-stamp">
              ← Browse the archive
            </Link>
          </div>
          <main className="flex flex-1 items-center justify-center px-6 py-10 lg:px-10">
            {/* useSearchParams() forces a Suspense boundary in a statically-analysed route (Next 15) */}
            <Suspense fallback={null}>
              <AuthPanel />
            </Suspense>
          </main>
        </div>
      </div>
    </div>
  );
}
