import type { ExpenseStatus } from "../../types/api"

const STATUS_STYLES: Record<ExpenseStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "text-text-muted" },
  pending_approval: { label: "Pending approval", className: "text-amber" },
  approved: { label: "Approved", className: "text-ledger" },
  rejected: { label: "Rejected", className: "text-red" },
  paid: { label: "Paid", className: "text-ledger" },
  cancelled: { label: "Cancelled", className: "text-text-muted line-through" },
}

export function ExpenseStatusLabel({ status }: { status: ExpenseStatus }) {
  const { label, className } = STATUS_STYLES[status]
  return <span className={`text-xs font-medium ${className}`}>{label}</span>
}
