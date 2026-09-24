import type { Budget } from "../../types/api"
import { formatKes } from "../../lib/format"
import { useBudgetStatus } from "./useBudgets"

export function BudgetRow({ budget }: { budget: Budget }) {
  const { data: status, isPending } = useBudgetStatus(budget.id)

  return (
    <li className="px-5 py-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-text-primary">{budget.department_name}</p>
          <p className="mt-0.5 text-xs text-text-muted">{budget.term_name}</p>
        </div>
        <p className="font-display text-base tabular-nums text-text-primary">{formatKes(budget.allocated_amount)}</p>
      </div>

      {isPending && <p className="mt-2 text-xs text-text-muted">Loading utilization…</p>}

      {status && (
        <div className="mt-3">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
            <div
              className={`h-full rounded-full ${status.is_over_budget ? "bg-red" : status.is_near_threshold ? "bg-amber" : "bg-ledger"}`}
              style={{ width: `${Math.min(Number(status.utilization_pct), 100)}%` }}
            />
          </div>
          <div className="mt-1.5 flex items-center justify-between text-xs">
            <span className={status.is_over_budget ? "font-medium text-red" : status.is_near_threshold ? "font-medium text-amber" : "text-text-muted"}>
              {formatKes(status.spent_amount)} spent ({status.utilization_pct}%)
              {status.is_over_budget && " — over budget"}
              {status.is_near_threshold && !status.is_over_budget && " — approaching limit"}
            </span>
            <span className="text-text-muted">{formatKes(status.remaining_amount)} remaining</span>
          </div>
        </div>
      )}
    </li>
  )
}
