"use client";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { QueueTableSkeleton } from "@/components/skeletons";
import { AccountsTable } from "@/components/admin/accounts-table";
import type { AdminAccount } from "@/types/wave2";

export default function AdminAccountsPage() {
  const { data, error, isLoading, mutate } = useApi<AdminAccount[]>("/api/admin/accounts");

  return (
    <>
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink/50">Administration</p>
      <h1 className="font-display-heading mt-0.5 text-2xl font-semibold text-ink">Accounts</h1>
      <p className="mt-1 text-sm text-ink/60">
        Every registered account — grant or revoke the reviewer role, set reviewer capacity, and deactivate
        accounts that should no longer sign in.
      </p>

      {isLoading && <QueueTableSkeleton label="Loading accounts…" />}

      {error && (
        <div className="mt-4">
          <ProblemAlert
            problem={
              error instanceof ClientApiError && error.problem.status === 404
                ? {
                    type: "about:blank",
                    title: "Account administration is not available yet",
                    status: 404,
                    detail: "The accounts endpoint has not been deployed. Try again after the next backend deploy.",
                  }
                : error instanceof ClientApiError
                  ? error.problem
                  : { type: "about:blank", title: "Something went wrong", status: 500 }
            }
          />
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState title="No accounts registered" hint="Accounts appear here as soon as someone registers." />
      )}

      {data && data.length > 0 && <AccountsTable accounts={data} onChanged={mutate} />}
    </>
  );
}
