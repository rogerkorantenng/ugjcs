"use client";
import { useState } from "react";
import { ProblemAlert } from "@/components/ui/alert";
import { postAccountAction, type AccountActionKind } from "@/components/admin/actions";
import { AccountActions } from "@/components/admin/account-actions";
import type { ProblemDetails } from "@/types/api";
import type { AdminAccount } from "@/types/wave2";

// The capacity control offers 1..10 — a reviewer always has at least one slot.
const CAPACITIES = Array.from({ length: 10 }, (_, i) => i + 1);

export function AccountRow({ account, onChanged }: { account: AdminAccount; onChanged: () => void }) {
  const [busy, setBusy] = useState<AccountActionKind | null>(null);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function run(kind: AccountActionKind, path: string, body: unknown) {
    setBusy(kind);
    setProblem(null);
    const failure = await postAccountAction(account.id, path, body);
    setBusy(null);
    if (failure) {
      setProblem(failure);
      return;
    }
    onChanged();
  }

  const capacityId = `capacity-${account.id}`;
  return (
    <>
      <tr className={`border-b border-rule transition-colors ${account.is_active ? "" : "opacity-60"}`} aria-busy={busy !== null}>
        <td className="py-2.5 pr-4">
          <span className="block font-medium text-ink">{account.full_name}</span>
          <span className="block font-mono text-xs text-ink/60">{account.email}</span>
          {!account.is_verified && (
            <span className="mt-0.5 block font-mono text-[10px] uppercase tracking-wide text-seal">Unverified</span>
          )}
        </td>
        <td className="pr-4 text-ink/70">{account.affiliation}</td>
        <td className="pr-4">
          <span className="flex flex-wrap gap-1">
            {account.roles.map((role) => (
              <span
                key={role}
                className="rounded-full border border-rule px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-ink/60"
              >
                {role.replaceAll("_", " ")}
              </span>
            ))}
          </span>
        </td>
        <td className="pr-4">
          <label htmlFor={capacityId} className="sr-only">
            Reviewer capacity for {account.email}
          </label>
          <select
            id={capacityId}
            value={account.reviewer_capacity}
            disabled={busy !== null}
            onChange={(event) => run("capacity", "capacity", { reviewer_capacity: Number(event.target.value) })}
            className="rounded-[3px] border border-rule bg-surface px-2 py-1 text-sm text-ink transition-colors
              hover:border-stamp/40 focus-visible:outline-2 focus-visible:outline-offset-1 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {CAPACITIES.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </td>
        <td className="pr-4">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase
              tracking-wide before:h-1.5 before:w-1.5 before:rounded-full before:content-['']
              ${account.is_active ? "border-verified/25 bg-verified/[0.06] text-verified before:bg-verified" : "border-seal/25 bg-seal/[0.06] text-seal before:bg-seal"}`}
          >
            {account.is_active ? "Active" : "Deactivated"}
          </span>
        </td>
        <td className="py-2.5 text-right">
          <AccountActions account={account} busy={busy} onRun={run} />
        </td>
      </tr>
      {problem && (
        <tr className="border-b border-rule">
          <td colSpan={6} className="py-2">
            <ProblemAlert problem={problem} />
          </td>
        </tr>
      )}
    </>
  );
}
