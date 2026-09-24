import { useState, type FormEvent } from "react"
import { useParams } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { formatDate, formatKes } from "../../lib/format"
import type { PaymentMethod } from "../../types/api"
import { InvoiceStatusLabel } from "./InvoiceStatusLabel"
import { useInvoice, useRecordPayment } from "./useFees"

const METHOD_LABELS: Record<PaymentMethod, string> = {
  mpesa: "M-Pesa",
  bank_transfer: "Bank transfer",
  card: "Card",
  cash: "Cash",
  other: "Other",
}

function apiErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  if (anyErr?.response?.status === 403) return "You do not have permission to do this."

  const data = anyErr?.response?.data
  // DRF's ValidationError, when raised with a plain string, serializes as
  // a bare JSON array (["message"]), not {non_field_errors: [...]} or
  // {detail: "..."} -- confirmed against the real backend response, not
  // assumed. Handle both shapes rather than guessing one.
  if (Array.isArray(data) && typeof data[0] === "string") return data[0]
  if (data && typeof data === "object") {
    const obj = data as { non_field_errors?: string[]; detail?: string }
    if (obj.non_field_errors?.length) return obj.non_field_errors[0]
    if (obj.detail) return obj.detail
  }
  return "That payment could not be recorded."
}

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: invoice, isPending, isError } = useInvoice(id!)
  const recordPayment = useRecordPayment()

  const [amount, setAmount] = useState("")
  const [method, setMethod] = useState<PaymentMethod>("mpesa")
  const [reference, setReference] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    try {
      await recordPayment.mutateAsync({
        invoice: Number(id),
        amount,
        method,
        reference_number: reference,
      })
      setAmount("")
      setReference("")
      setShowForm(false)
    } catch (err) {
      setFormError(apiErrorMessage(err))
    }
  }

  if (isPending) {
    return (
      <AppShell title="Invoice">
        <p className="text-sm text-text-muted">Loading…</p>
      </AppShell>
    )
  }

  if (isError || !invoice) {
    return (
      <AppShell title="Invoice">
        <p className="border-l-2 border-red pl-3 text-sm text-red">This invoice could not be found.</p>
      </AppShell>
    )
  }

  const canRecordPayment = invoice.status === "issued" || invoice.status === "partially_paid"

  return (
    <AppShell title={invoice.student_name}>
      <div className="max-w-2xl">
        <div className="flex items-center justify-between">
          <InvoiceStatusLabel status={invoice.status} />
          <p className="font-display text-2xl font-medium tabular-nums text-text-primary">{formatKes(invoice.total_amount)}</p>
        </div>

        <dl className="mt-6 grid grid-cols-3 gap-4 text-sm">
          <div>
            <dt className="text-text-muted">Total</dt>
            <dd className="mt-0.5 font-display text-lg tabular-nums text-text-primary">{formatKes(invoice.total_amount)}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Paid</dt>
            <dd className="mt-0.5 font-display text-lg tabular-nums text-ledger">{formatKes(invoice.amount_paid)}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Balance</dt>
            <dd className={`mt-0.5 font-display text-lg tabular-nums ${Number(invoice.balance) > 0 ? "text-amber" : "text-text-primary"}`}>
              {formatKes(invoice.balance)}
            </dd>
          </div>
        </dl>

        <h2 className="mt-8 font-display text-lg font-medium text-text-primary">Line items</h2>
        <ul className="mt-3 divide-y divide-line rounded border border-line bg-surface">
          {invoice.items.map((item) => (
            <li key={item.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <span className="text-text-primary">
                {item.fee_category_name}
                {item.description && <span className="text-text-muted"> — {item.description}</span>}
              </span>
              <span className="tabular-nums text-text-primary">{formatKes(item.amount)}</span>
            </li>
          ))}
        </ul>

        <div className="mt-8 flex items-center justify-between">
          <h2 className="font-display text-lg font-medium text-text-primary">Record a payment</h2>
          {canRecordPayment && !showForm && (
            <button onClick={() => setShowForm(true)} className="text-sm font-medium text-ledger hover:underline">
              + Record payment
            </button>
          )}
        </div>

        {!canRecordPayment && (
          <p className="mt-2 text-sm text-text-muted">
            {invoice.status === "paid" ? "This invoice is fully paid." : "This invoice is cancelled."}
          </p>
        )}

        {showForm && (
          <form onSubmit={handleSubmit} className="mt-3 max-w-sm space-y-3 rounded border border-line bg-surface p-4">
            <div>
              <label htmlFor="amount" className="block text-xs font-medium text-text-primary">
                Amount (outstanding: {formatKes(invoice.balance)})
              </label>
              <input
                id="amount"
                required
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="mt-1 block w-full rounded border border-line px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
              />
            </div>
            <div>
              <label htmlFor="method" className="block text-xs font-medium text-text-primary">
                Method
              </label>
              <select
                id="method"
                value={method}
                onChange={(e) => setMethod(e.target.value as PaymentMethod)}
                className="mt-1 block w-full rounded border border-line px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
              >
                {Object.entries(METHOD_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="reference" className="block text-xs font-medium text-text-primary">
                Reference number (optional)
              </label>
              <input
                id="reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                className="mt-1 block w-full rounded border border-line px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
              />
            </div>

            {formError && <p className="border-l-2 border-red pl-3 text-sm text-red">{formError}</p>}

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={recordPayment.isPending}
                className="rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
              >
                {recordPayment.isPending ? "Recording…" : "Record payment"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded border border-line px-3.5 py-2 text-sm font-medium text-text-primary hover:bg-paper"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        <p className="mt-6 text-xs text-text-muted">Invoice created {formatDate(invoice.created_at)}</p>
      </div>
    </AppShell>
  )
}
