"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { AccountActionKind } from "@/components/admin/actions";
import type { AdminAccount } from "@/types/wave2";

/**
 * The per-row action buttons: grant/revoke the reviewer role, and the active toggle.
 * Deactivating locks someone out, so it takes the portal's usual two-step confirmation;
 * reactivating is a plain undo and needs only one click.
 */
export function AccountActions({
  account,
  busy,
  onRun,
}: {
  account: AdminAccount;
  busy: AccountActionKind | null;
  onRun: (kind: AccountActionKind, path: string, body: unknown) => Promise<void>;
}) {
  const [confirmingDeactivate, setConfirmingDeactivate] = useState(false);
  const isReviewer = account.roles.includes("reviewer");

  if (confirmingDeactivate) {
    return (
      <span className="inline-flex flex-wrap items-center justify-end gap-2">
        <span className="text-xs font-medium text-seal">Deactivate {account.email}?</span>
        <Button
          variant="danger"
          className="px-2.5 py-1 text-xs"
          isLoading={busy === "active"}
          onClick={async () => {
            await onRun("active", "active", { is_active: false });
            setConfirmingDeactivate(false);
          }}
        >
          {busy === "active" ? "Deactivating…" : "Confirm"}
        </Button>
        <Button
          variant="secondary"
          className="px-2.5 py-1 text-xs"
          disabled={busy !== null}
          onClick={() => setConfirmingDeactivate(false)}
        >
          Cancel
        </Button>
      </span>
    );
  }
  return (
    <span className="inline-flex flex-wrap items-center justify-end gap-2">
      <Button
        variant="secondary"
        className="px-2.5 py-1 text-xs"
        isLoading={busy === "role"}
        disabled={busy !== null}
        onClick={() => onRun("role", "roles", { role: "reviewer", grant: !isReviewer })}
      >
        {isReviewer ? "Revoke reviewer" : "Grant reviewer"}
      </Button>
      {account.is_active ? (
        <Button
          variant="secondary"
          className="border-seal/40 px-2.5 py-1 text-xs text-seal hover:border-seal hover:bg-seal/5"
          disabled={busy !== null}
          onClick={() => setConfirmingDeactivate(true)}
        >
          Deactivate
        </Button>
      ) : (
        <Button
          variant="secondary"
          className="px-2.5 py-1 text-xs"
          isLoading={busy === "active"}
          disabled={busy !== null}
          onClick={() => onRun("active", "active", { is_active: true })}
        >
          {busy === "active" ? "Reactivating…" : "Reactivate"}
        </Button>
      )}
    </span>
  );
}
