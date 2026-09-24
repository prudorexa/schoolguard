import { Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { formatDate, formatKes } from "../../lib/format"
import { PurchaseRequestStatusLabel } from "./PurchaseRequestStatusLabel"
import { usePurchaseRequests } from "./useProcurement"

export function PurchaseRequestsListPage() {
  const { data, isPending, isError } = usePurchaseRequests()

  return (
    <AppShell title="Procurement">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-text-muted">Purchase requests, quotations, orders, and deliveries.</p>
        <Link
          to="/procurement/new"
          className="flex items-center gap-1.5 rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft"
        >
          <Plus className="h-4 w-4" />
          New request
        </Link>
      </div>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">
          You don't have permission to view purchase requests, or they could not be loaded.
        </p>
      )}

      {data && data.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No purchase requests yet.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.map((pr) => (
            <li key={pr.id}>
              <Link to={`/procurement/${pr.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-paper">
                <div>
                  <p className="text-sm font-medium text-text-primary">{pr.title}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {pr.department_name} · {pr.requested_by_email} · {formatDate(pr.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <PurchaseRequestStatusLabel status={pr.status} />
                  <p className="font-display text-base tabular-nums text-text-primary">{formatKes(pr.estimated_amount)}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}
