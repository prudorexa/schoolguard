import { Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { formatDate, formatKes } from "../../lib/format"
import { ExpenseStatusLabel } from "./ExpenseStatusLabel"
import { useExpenses } from "./useExpenses"

export function ExpensesListPage() {
  const { data, isPending, isError } = useExpenses()

  return (
    <AppShell title="Expenses">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-text-muted">Requests move from draft through approval to payment.</p>
        <Link
          to="/expenses/new"
          className="flex items-center gap-1.5 rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft"
        >
          <Plus className="h-4 w-4" />
          New request
        </Link>
      </div>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">
          You don't have permission to view expenses, or they could not be loaded.
        </p>
      )}

      {data && data.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No expense requests yet.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.map((expense) => (
            <li key={expense.id}>
              <Link to={`/expenses/${expense.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-paper">
                <div>
                  <p className="text-sm font-medium text-text-primary">{expense.title}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {expense.department_name} · {expense.requested_by_email} · {formatDate(expense.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <ExpenseStatusLabel status={expense.status} />
                  <p className="font-display text-base tabular-nums text-text-primary">{formatKes(expense.amount)}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}
