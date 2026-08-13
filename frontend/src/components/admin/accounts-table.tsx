"use client";
import { AccountRow } from "@/components/admin/account-row";
import type { AdminAccount } from "@/types/wave2";

/**
 * The admin console's account table. Every mutation happens row-by-row; `onChanged`
 * refetches the whole list so a row never shows state the server no longer agrees with.
 */
export function AccountsTable({ accounts, onChanged }: { accounts: AdminAccount[]; onChanged: () => void }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[56rem] text-left text-sm">
        <caption className="sr-only">Registered accounts</caption>
        <thead>
          <tr className="border-b border-rule text-ink/60">
            <th scope="col" className="py-2 pr-4 font-medium">Account</th>
            <th scope="col" className="pr-4 font-medium">Affiliation</th>
            <th scope="col" className="pr-4 font-medium">Roles</th>
            <th scope="col" className="pr-4 font-medium">Capacity</th>
            <th scope="col" className="pr-4 font-medium">Status</th>
            <th scope="col" className="text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <AccountRow key={account.id} account={account} onChanged={onChanged} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
