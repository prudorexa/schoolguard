import { useState } from "react"
import { useParams } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useAuth } from "../../lib/auth"
import { formatDate, formatKes } from "../../lib/format"
import { PurchaseRequestStatusLabel } from "./PurchaseRequestStatusLabel"
import {
  useApprovePurchaseRequest,
  useCreateQuotation,
  useDiscrepancyReport,
  useIssuePurchaseOrder,
  usePurchaseOrderForRequest,
  usePurchaseRequest,
  useQuotationsForRequest,
  useRecordDelivery,
  useRecordSupplierInvoice,
  useRejectPurchaseRequest,
  useSubmitPurchaseRequest,
  useSuppliers,
} from "./useProcurement"

function apiErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  if (anyErr?.response?.status === 403) return "You do not have permission to do this."
  const data = anyErr?.response?.data
  if (Array.isArray(data) && typeof data[0] === "string") return data[0]
  if (data && typeof data === "object") {
    const obj = data as { non_field_errors?: string[]; detail?: string }
    if (obj.non_field_errors?.length) return obj.non_field_errors[0]
    if (obj.detail) return obj.detail
  }
  return "That action could not be completed."
}

function ActionButton({
  label,
  onClick,
  pending,
  variant = "primary",
}: {
  label: string
  onClick: () => void
  pending?: boolean
  variant?: "primary" | "secondary" | "danger"
}) {
  const classes = {
    primary: "bg-ink text-text-inverse hover:bg-ink-soft",
    secondary: "border border-line bg-surface text-text-primary hover:bg-paper",
    danger: "bg-red text-text-inverse hover:bg-red/90",
  }[variant]
  return (
    <button type="button" onClick={onClick} disabled={pending} className={`rounded px-3.5 py-2 text-sm font-medium disabled:opacity-60 ${classes}`}>
      {pending ? "Working…" : label}
    </button>
  )
}

export function PurchaseRequestDetailPage() {
  const { id } = useParams<{ id: string }>()
  const prId = Number(id)
  const { user } = useAuth()
  const { data: pr, isPending, isError } = usePurchaseRequest(id!)

  const [actionError, setActionError] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState("")
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [quoteSupplier, setQuoteSupplier] = useState("")
  const [quoteAmount, setQuoteAmount] = useState("")
  const [deliveryNotes, setDeliveryNotes] = useState("")
  const [invoiceNumber, setInvoiceNumber] = useState("")
  const [invoiceAmount, setInvoiceAmount] = useState("")

  const submit = useSubmitPurchaseRequest()
  const approve = useApprovePurchaseRequest()
  const reject = useRejectPurchaseRequest()
  const suppliersQuery = useSuppliers()
  const quotationsQuery = useQuotationsForRequest(prId)
  const createQuotation = useCreateQuotation()
  const issuePO = useIssuePurchaseOrder()
  const poQuery = usePurchaseOrderForRequest(prId, !!pr?.has_purchase_order)
  const recordDelivery = useRecordDelivery()
  const recordInvoice = useRecordSupplierInvoice()
  const discrepancyQuery = useDiscrepancyReport(poQuery.data?.id ?? 0, !!poQuery.data && poQuery.data.has_invoice)

  async function run(action: () => Promise<unknown>) {
    setActionError(null)
    try {
      await action()
    } catch (err) {
      setActionError(apiErrorMessage(err))
    }
  }

  if (isPending) {
    return (
      <AppShell title="Purchase request">
        <p className="text-sm text-text-muted">Loading…</p>
      </AppShell>
    )
  }

  if (isError || !pr) {
    return (
      <AppShell title="Purchase request">
        <p className="border-l-2 border-red pl-3 text-sm text-red">This request could not be found.</p>
      </AppShell>
    )
  }

  const isOwnRequest = user?.email === pr.requested_by_email
  const po = poQuery.data

  return (
    <AppShell title={pr.title}>
      <div className="max-w-2xl">
        <div className="flex items-center justify-between">
          <PurchaseRequestStatusLabel status={pr.status} />
          <p className="font-display text-2xl font-medium tabular-nums text-text-primary">{formatKes(pr.estimated_amount)}</p>
        </div>

        <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-text-muted">Department</dt>
            <dd className="mt-0.5 text-text-primary">{pr.department_name}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Requested by</dt>
            <dd className="mt-0.5 text-text-primary">
              {pr.requested_by_email} {isOwnRequest && <span className="text-text-muted">(you)</span>}
            </dd>
          </div>
        </dl>

        {pr.rejection_reason && (
          <p className="mt-4 border-l-2 border-red pl-3 text-sm text-text-primary">Rejected: {pr.rejection_reason}</p>
        )}

        <h2 className="mt-8 font-display text-lg font-medium text-text-primary">Line items</h2>
        <ul className="mt-3 divide-y divide-line rounded border border-line bg-surface">
          {pr.items.map((item) => (
            <li key={item.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <span className="text-text-primary">
                {item.description} <span className="text-text-muted">× {item.quantity}</span>
              </span>
              <span className="tabular-nums text-text-primary">{formatKes(item.estimated_total)}</span>
            </li>
          ))}
        </ul>

        {actionError && <p className="mt-4 border-l-2 border-red pl-3 text-sm text-red">{actionError}</p>}

        {isOwnRequest && pr.status === "pending_approval" && (
          <p className="mt-4 text-xs text-text-muted">You requested this, so you won't be able to approve or reject it yourself.</p>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          {pr.status === "draft" && (
            <ActionButton label="Submit for approval" pending={submit.isPending} onClick={() => run(() => submit.mutateAsync({ id: pr.id }))} />
          )}
          {pr.status === "pending_approval" && (
            <>
              <ActionButton label="Approve" pending={approve.isPending} onClick={() => run(() => approve.mutateAsync({ id: pr.id }))} />
              {!showRejectForm && <ActionButton label="Reject" variant="danger" onClick={() => setShowRejectForm(true)} />}
            </>
          )}
        </div>

        {showRejectForm && pr.status === "pending_approval" && (
          <div className="mt-4 max-w-md">
            <label htmlFor="reason" className="block text-sm font-medium text-text-primary">
              Reason for rejection
            </label>
            <textarea
              id="reason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={2}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
            <div className="mt-2 flex gap-2">
              <ActionButton
                label="Confirm rejection"
                variant="danger"
                pending={reject.isPending}
                onClick={() => run(() => reject.mutateAsync({ id: pr.id, payload: { reason: rejectReason } }))}
              />
              <ActionButton label="Cancel" variant="secondary" onClick={() => setShowRejectForm(false)} />
            </div>
          </div>
        )}

        {/* --- Quotations, once approved --- */}
        {(pr.status === "approved" || pr.status === "converted") && (
          <section className="mt-10">
            <h2 className="font-display text-lg font-medium text-text-primary">Quotations</h2>

            {quotationsQuery.data && quotationsQuery.data.length > 0 && (
              <ul className="mt-3 divide-y divide-line rounded border border-line bg-surface">
                {quotationsQuery.data.map((q) => (
                  <li key={q.id} className="flex items-center justify-between px-4 py-3 text-sm">
                    <div>
                      <span className="text-text-primary">{q.supplier_name}</span>
                      {q.notes && <span className="text-text-muted"> — {q.notes}</span>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="tabular-nums text-text-primary">{formatKes(q.amount)}</span>
                      {pr.status === "approved" && (
                        <ActionButton
                          label="Issue PO"
                          pending={issuePO.isPending}
                          onClick={() => run(() => issuePO.mutateAsync({ purchase_request: pr.id, quotation: q.id }))}
                        />
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {pr.status === "approved" && (
              <div className="mt-4 flex flex-wrap items-end gap-2 rounded border border-line bg-surface p-4">
                <div>
                  <label htmlFor="quote-supplier" className="block text-xs font-medium text-text-primary">
                    Supplier
                  </label>
                  <select
                    id="quote-supplier"
                    value={quoteSupplier}
                    onChange={(e) => setQuoteSupplier(e.target.value)}
                    className="mt-1 rounded border border-line px-2 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                  >
                    <option value="" disabled>
                      {suppliersQuery.isPending ? "Loading…" : "Select supplier"}
                    </option>
                    {suppliersQuery.data?.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="quote-amount" className="block text-xs font-medium text-text-primary">
                    Amount
                  </label>
                  <input
                    id="quote-amount"
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={quoteAmount}
                    onChange={(e) => setQuoteAmount(e.target.value)}
                    className="mt-1 w-32 rounded border border-line px-2 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                  />
                </div>
                <ActionButton
                  label="Add quotation"
                  variant="secondary"
                  pending={createQuotation.isPending}
                  onClick={() =>
                    run(() =>
                      createQuotation.mutateAsync({
                        purchase_request: pr.id,
                        supplier: Number(quoteSupplier),
                        amount: quoteAmount,
                      }),
                    )
                  }
                />
              </div>
            )}
          </section>
        )}

        {/* --- Purchase order, once issued --- */}
        {po && (
          <section className="mt-10">
            <h2 className="font-display text-lg font-medium text-text-primary">Purchase order</h2>
            <div className="mt-3 rounded border border-line bg-surface p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-text-primary">{po.supplier_name}</span>
                <span className="font-display text-base tabular-nums text-text-primary">{formatKes(po.amount)}</span>
              </div>
              <p className="mt-1 text-xs text-text-muted">Status: {po.status} · issued by {po.issued_by_email}</p>
            </div>

            {!po.has_delivery && (
              <div className="mt-4 rounded border border-line bg-surface p-4">
                <p className="text-sm font-medium text-text-primary">Record delivery</p>
                <textarea
                  value={deliveryNotes}
                  onChange={(e) => setDeliveryNotes(e.target.value)}
                  placeholder="Notes (optional)"
                  rows={2}
                  className="mt-2 block w-full rounded border border-line px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                />
                <div className="mt-2">
                  <ActionButton
                    label="Mark as delivered"
                    pending={recordDelivery.isPending}
                    onClick={() => run(() => recordDelivery.mutateAsync({ purchase_order: po.id, is_complete: true, notes: deliveryNotes }))}
                  />
                </div>
              </div>
            )}

            {po.has_delivery && !po.has_invoice && (
              <div className="mt-4 rounded border border-line bg-surface p-4">
                <p className="text-sm font-medium text-text-primary">Record supplier invoice</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <input
                    value={invoiceNumber}
                    onChange={(e) => setInvoiceNumber(e.target.value)}
                    placeholder="Invoice number"
                    className="rounded border border-line px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                  />
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={invoiceAmount}
                    onChange={(e) => setInvoiceAmount(e.target.value)}
                    placeholder="Amount"
                    className="w-32 rounded border border-line px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                  />
                  <ActionButton
                    label="Record invoice"
                    pending={recordInvoice.isPending}
                    onClick={() =>
                      run(() =>
                        recordInvoice.mutateAsync({ purchase_order: po.id, invoice_number: invoiceNumber, amount: invoiceAmount }),
                      )
                    }
                  />
                </div>
              </div>
            )}

            {po.has_invoice && discrepancyQuery.data && (
              <div className="mt-4 rounded border border-line bg-surface p-4">
                <p className="text-sm font-medium text-text-primary">Discrepancy check</p>
                <dl className="mt-2 grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <dt className="text-text-muted">Requested</dt>
                    <dd className="tabular-nums text-text-primary">{formatKes(discrepancyQuery.data.requested_amount)}</dd>
                  </div>
                  <div>
                    <dt className="text-text-muted">PO amount</dt>
                    <dd className="tabular-nums text-text-primary">{formatKes(discrepancyQuery.data.po_amount)}</dd>
                  </div>
                  <div>
                    <dt className="text-text-muted">Invoiced</dt>
                    <dd className="tabular-nums text-text-primary">
                      {discrepancyQuery.data.invoiced_amount ? formatKes(discrepancyQuery.data.invoiced_amount) : "—"}
                    </dd>
                  </div>
                </dl>
                {discrepancyQuery.data.flags.length === 0 ? (
                  <p className="mt-3 text-sm text-ledger">No discrepancies flagged.</p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {discrepancyQuery.data.flags.map((flag, i) => (
                      <li key={i} className="border-l-2 border-red pl-3 text-sm text-text-primary">
                        {flag}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>
        )}

        <p className="mt-8 text-xs text-text-muted">Requested {formatDate(pr.created_at)}</p>
      </div>
    </AppShell>
  )
}
