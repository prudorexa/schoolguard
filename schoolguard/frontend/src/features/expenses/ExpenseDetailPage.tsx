import { useState } from "react"
import { useParams } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useAuth } from "../../lib/auth"
import { formatDate, formatKes } from "../../lib/format"
import { ExpenseStatusLabel } from "./ExpenseStatusLabel"
import {
  useApproveExpense,
  useCancelExpense,
  useExpense,
  useMarkExpensePaid,
  useRejectExpense,
  useSubmitExpense,
} from "./useExpenses"

function apiErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  if (anyErr?.response?.status === 403) return "You do not have permission to do this."

  const data = anyErr?.response?.data
  // DRF's ValidationError, when raised with a plain string (as every
  // workflow rule in services.py does), serializes as a bare JSON array
  // (["message"]), not {detail: "..."} -- confirmed against the real
  // backend response, not assumed.
  if (Array.isArray(data) && typeof data[0] === "string") return data[0]
  if (data && typeof data === "object") {
    const obj = data as { detail?: string }
    if (obj.detail) return obj.detail
  }
  return "That action could not be completed."
}

export function ExpenseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { data: expense, isPending, isError } = useExpense(id!)
  const [actionError, setActionError] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState("")
  const [showRejectForm, setShowRejectForm] = useState(false)

  const submit = useSubmitExpense()
  const approve = useApproveExpense()
  const reject = useRejectExpense()
  const markPaid = useMarkExpensePaid()
  const cancel = useCancelExpense()

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
      <AppShell title="Expense request">
        <p className="text-sm text-text-muted">Loading…</p>
      </AppShell>
    )
  }

  if (isError || !expense) {
    return (
      <AppShell title="Expense request">
        <p className="border-l-2 border-red pl-3 text-sm text-red">This request could not be found.</p>
      </AppShell>
    )
  }

  const isOwnRequest = user?.email === expense.requested_by_email

  return (
    <AppShell title={expense.title}>
      <div className="max-w-2xl">
        <div className="flex items-center justify-between">
          <ExpenseStatusLabel status={expense.status} />
          <p className="font-display text-2xl font-medium tabular-nums text-text-primary">{formatKes(expense.amount)}</p>
        </div>

        <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-text-muted">Department</dt>
            <dd className="mt-0.5 text-text-primary">{expense.department_name}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Requested by</dt>
            <dd className="mt-0.5 text-text-primary">
              {expense.requested_by_email} {isOwnRequest && <span className="text-text-muted">(you)</span>}
            </dd>
          </div>
          <div>
            <dt className="text-text-muted">Requested on</dt>
            <dd className="mt-0.5 text-text-primary">{formatDate(expense.created_at)}</dd>
          </div>
          {expense.approved_by_email && (
            <div>
              <dt className="text-text-muted">{expense.status === "rejected" ? "Rejected by" : "Approved by"}</dt>
              <dd className="mt-0.5 text-text-primary">{expense.approved_by_email}</dd>
            </div>
          )}
        </dl>

        {expense.rejection_reason && (
          <p className="mt-4 border-l-2 border-red pl-3 text-sm text-text-primary">
            Rejected: {expense.rejection_reason}
          </p>
        )}

        <h2 className="mt-8 font-display text-lg font-medium text-text-primary">Line items</h2>
        <ul className="mt-3 divide-y divide-line rounded border border-line bg-surface">
          {expense.items.map((item) => (
            <li key={item.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <span className="text-text-primary">{item.description}</span>
              <span className="tabular-nums text-text-primary">{formatKes(item.amount)}</span>
            </li>
          ))}
        </ul>

        {actionError && <p className="mt-4 border-l-2 border-red pl-3 text-sm text-red">{actionError}</p>}

        {isOwnRequest && expense.status === "pending_approval" && (
          <p className="mt-4 text-xs text-text-muted">
            You requested this, so you won't be able to approve or reject it yourself.
          </p>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          {expense.status === "draft" && (
            <>
              <ActionButton label="Submit for approval" pending={submit.isPending} onClick={() => run(() => submit.mutateAsync({ id: expense.id }))} />
              <ActionButton
                label="Cancel"
                variant="secondary"
                pending={cancel.isPending}
                onClick={() => run(() => cancel.mutateAsync({ id: expense.id }))}
              />
            </>
          )}

          {expense.status === "pending_approval" && (
            <>
              <ActionButton label="Approve" pending={approve.isPending} onClick={() => run(() => approve.mutateAsync({ id: expense.id }))} />
              {!showRejectForm && (
                <ActionButton label="Reject" variant="danger" onClick={() => setShowRejectForm(true)} />
              )}
            </>
          )}

          {expense.status === "approved" && (
            <ActionButton label="Mark as paid" pending={markPaid.isPending} onClick={() => run(() => markPaid.mutateAsync({ id: expense.id }))} />
          )}
        </div>

        {showRejectForm && expense.status === "pending_approval" && (
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
                onClick={() => run(() => reject.mutateAsync({ id: expense.id, payload: { reason: rejectReason } }))}
              />
              <ActionButton label="Cancel" variant="secondary" onClick={() => setShowRejectForm(false)} />
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
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
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      className={`rounded px-3.5 py-2 text-sm font-medium disabled:opacity-60 ${classes}`}
    >
      {pending ? "Working…" : label}
    </button>
  )
}
