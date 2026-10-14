import { Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useSuppliers } from "./useSuppliers"

export function SuppliersListPage() {
  const { data, isPending, isError } = useSuppliers()

  return (
    <AppShell title="Suppliers">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-text-muted">Vendors used for expenses and procurement.</p>
        <Link
          to="/suppliers/new"
          className="flex items-center gap-1.5 rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft"
        >
          <Plus className="h-4 w-4" />
          New supplier
        </Link>
      </div>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">
          You don't have permission to view suppliers, or they could not be loaded.
        </p>
      )}

      {data && data.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No suppliers registered yet.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.map((supplier) => (
            <li key={supplier.id} className="flex items-center justify-between px-5 py-3.5">
              <div>
                <p className="text-sm font-medium text-text-primary">{supplier.name}</p>
                <p className="mt-0.5 text-xs text-text-muted">
                  {[supplier.contact_person, supplier.phone, supplier.email].filter(Boolean).join(" · ") || "No contact details"}
                </p>
              </div>
              <span className={`text-xs font-medium ${supplier.status === "active" ? "text-ledger" : "text-text-muted"}`}>
                {supplier.status === "active" ? "Active" : "Inactive"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}
