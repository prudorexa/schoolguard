import { Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { BudgetRow } from "./BudgetRow"
import { useBudgets } from "./useBudgets"

export function BudgetsListPage() {
  const { data, isPending, isError } = useBudgets()

  return (
    <AppShell title="Budgets">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-text-muted">Allocated per department per term. Spend is computed from real expenses, never stored.</p>
        <Link
          to="/budgets/new"
          className="flex items-center gap-1.5 rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft"
        >
          <Plus className="h-4 w-4" />
          New budget
        </Link>
      </div>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">
          You don't have permission to view budgets, or they could not be loaded.
        </p>
      )}

      {data && data.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No budgets set yet.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.map((budget) => (
            <BudgetRow key={budget.id} budget={budget} />
          ))}
        </ul>
      )}
    </AppShell>
  )
}
