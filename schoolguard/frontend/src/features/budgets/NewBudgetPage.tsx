import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useCreateBudget, useDepartments, useTerms } from "./useBudgets"

function apiErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  if (anyErr?.response?.status === 403) return "You do not have permission to do this."
  const data = anyErr?.response?.data
  // Two different shapes are possible for the same underlying "duplicate
  // budget for this term+department" rule, depending on which validation
  // path catches it: DRF's automatic UniqueTogetherValidator fires here
  // (because both constraint fields -- term, department -- are real
  // serializer fields) and returns {non_field_errors: [...]}. Other
  // "unique per school" models fall through to a bare array instead (see
  // Suppliers), because `school` isn't a serializer field DRF can build
  // that validator from. Confirmed live, not assumed -- handle both.
  if (Array.isArray(data) && typeof data[0] === "string") return data[0]
  if (data && typeof data === "object") {
    const obj = data as { non_field_errors?: string[] }
    if (obj.non_field_errors?.length) return obj.non_field_errors[0]
  }
  return "Could not create the budget. Check that all fields are filled in correctly."
}

export function NewBudgetPage() {
  const navigate = useNavigate()
  const departmentsQuery = useDepartments()
  const termsQuery = useTerms()
  const createBudget = useCreateBudget()

  const [departmentId, setDepartmentId] = useState("")
  const [termId, setTermId] = useState("")
  const [amount, setAmount] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createBudget.mutateAsync({
        term: Number(termId),
        department: Number(departmentId),
        allocated_amount: amount,
      })
      navigate("/budgets")
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <AppShell title="New budget">
      <form onSubmit={handleSubmit} className="max-w-md space-y-5">
        <div>
          <label htmlFor="department" className="block text-sm font-medium text-text-primary">
            Department
          </label>
          <select
            id="department"
            required
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          >
            <option value="" disabled>
              {departmentsQuery.isPending ? "Loading…" : "Select a department"}
            </option>
            {departmentsQuery.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="term" className="block text-sm font-medium text-text-primary">
            Term
          </label>
          <select
            id="term"
            required
            value={termId}
            onChange={(e) => setTermId(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          >
            <option value="" disabled>
              {termsQuery.isPending ? "Loading…" : "Select a term"}
            </option>
            {termsQuery.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="amount" className="block text-sm font-medium text-text-primary">
            Allocated amount
          </label>
          <input
            id="amount"
            required
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          />
        </div>

        {error && <p className="border-l-2 border-red pl-3 text-sm text-red">{error}</p>}

        <button
          type="submit"
          disabled={createBudget.isPending}
          className="rounded bg-ink px-4 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
        >
          {createBudget.isPending ? "Saving…" : "Create budget"}
        </button>
      </form>
    </AppShell>
  )
}
