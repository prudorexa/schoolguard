import type { InvoiceStatus } from "../../types/api"

const STATUS_STYLES: Record<InvoiceStatus, { label: string; className: string }> = {
  issued: { label: "Issued", className: "text-amber" },
  partially_paid: { label: "Partially paid", className: "text-amber" },
  paid: { label: "Paid", className: "text-ledger" },
  cancelled: { label: "Cancelled", className: "text-text-muted line-through" },
}

export function InvoiceStatusLabel({ status }: { status: InvoiceStatus }) {
  const { label, className } = STATUS_STYLES[status]
  return <span className={`text-xs font-medium ${className}`}>{label}</span>
}
