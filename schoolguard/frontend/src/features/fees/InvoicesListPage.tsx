import { Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { formatDate, formatKes } from "../../lib/format"
import { InvoiceStatusLabel } from "./InvoiceStatusLabel"
import { useInvoices } from "./useFees"

export function InvoicesListPage() {
  const { data, isPending, isError } = useInvoices()

  return (
    <AppShell title="Fees">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-text-muted">Invoices, balances, and payments.</p>
        <Link
          to="/fees/new"
          className="flex items-center gap-1.5 rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft"
        >
          <Plus className="h-4 w-4" />
          New invoice
        </Link>
      </div>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">
          You don't have permission to view invoices, or they could not be loaded.
        </p>
      )}

      {data && data.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No invoices yet.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.map((invoice) => (
            <li key={invoice.id}>
              <Link to={`/fees/${invoice.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-paper">
                <div>
                  <p className="text-sm font-medium text-text-primary">{invoice.student_name}</p>
                  <p className="mt-0.5 text-xs text-text-muted">{formatDate(invoice.created_at)}</p>
                </div>
                <div className="flex items-center gap-6">
                  <InvoiceStatusLabel status={invoice.status} />
                  <div className="text-right">
                    <p className="font-display text-base tabular-nums text-text-primary">{formatKes(invoice.total_amount)}</p>
                    {Number(invoice.balance) > 0 && (
                      <p className="text-xs text-amber">{formatKes(invoice.balance)} outstanding</p>
                    )}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}
