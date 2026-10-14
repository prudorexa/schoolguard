import { AlertTriangle, ShieldAlert } from "lucide-react"

import type { FinancialAlert } from "../../types/api"

const CATEGORY_LABELS: Record<string, string> = {
  budget_exceeded: "Budget exceeded",
  invoice_mismatch: "Invoice mismatch",
  duplicate_payment: "Duplicate payment",
  pending_approvals: "Pending approvals",
  overdue_invoice: "Overdue invoice",
}

export function AlertsList({ alerts }: { alerts: FinancialAlert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
        No issues flagged right now.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-line rounded border border-line bg-surface">
      {alerts.map((alert, i) => {
        const isCritical = alert.severity === "critical"
        return (
          <li
            key={i}
            className={`flex items-start gap-3 border-l-2 px-5 py-4 ${isCritical ? "border-l-red" : "border-l-amber"}`}
          >
            {isCritical ? (
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red" />
            ) : (
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
            )}
            <div>
              <p className={`text-xs font-medium ${isCritical ? "text-red" : "text-amber"}`}>
                {CATEGORY_LABELS[alert.category] ?? alert.category}
              </p>
              <p className="mt-0.5 text-sm text-text-primary">{alert.message}</p>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
