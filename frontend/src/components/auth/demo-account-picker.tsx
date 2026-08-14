"use client";
import { DEMO_ACCOUNTS } from "@/lib/demo-accounts";

/**
 * Role chips that fill the sign-in form's email field. Shown on the sign-in tab only —
 * on the sign-up tab the whole point is to mint a new account, so offering a seeded one
 * there would contradict the form beside it.
 *
 * `aria-pressed` rather than a radio group: these are shortcuts that write into a field
 * the reader can still edit by hand, not a selection the form submits. Whichever chip
 * matches the current address reads as pressed, so typing an address by hand un-presses
 * them all without any extra bookkeeping.
 */
export function DemoAccountPicker({
  selected,
  onPick,
}: {
  selected: string;
  onPick: (email: string) => void;
}) {
  return (
    <section aria-labelledby="demo-accounts" className="mt-6 rounded-[3px] border border-rule bg-surface/60 p-4">
      <h2 id="demo-accounts" className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-ink/50">
        Demo accounts
      </h2>
      <p className="mt-1.5 text-xs leading-relaxed text-ink/60">
        Pick a desk to fill in its email address. Passwords are in the submission notes and
        are typed by hand.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {DEMO_ACCOUNTS.map((account) => {
          const active = account.email === selected;
          return (
            <button
              key={account.email}
              type="button"
              aria-pressed={active}
              title={account.email}
              onClick={() => onPick(account.email)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors duration-150
                focus-visible:outline-2 focus-visible:outline-offset-2 ${
                  active
                    ? "border-stamp bg-stamp text-paper"
                    : "border-rule bg-paper text-ink/75 hover:border-stamp/50 hover:text-stamp"
                }`}
            >
              {account.label}
            </button>
          );
        })}
      </div>
    </section>
  );
}
