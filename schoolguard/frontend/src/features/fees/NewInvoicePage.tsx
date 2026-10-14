import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useCreateInvoice, useFeeCategories, useStudents, useTerms } from "./useFees"

interface LineItem {
  fee_category_id: string
  description: string
  amount: string
}

export function NewInvoicePage() {
  const navigate = useNavigate()
  const studentsQuery = useStudents()
  const termsQuery = useTerms()
  const feeCategoriesQuery = useFeeCategories()
  const createInvoice = useCreateInvoice()

  const [studentId, setStudentId] = useState("")
  const [termId, setTermId] = useState("")
  const [items, setItems] = useState<LineItem[]>([{ fee_category_id: "", description: "", amount: "" }])
  const [error, setError] = useState<string | null>(null)

  function updateItem(index: number, field: keyof LineItem, value: string) {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)))
  }

  function addItem() {
    setItems((prev) => [...prev, { fee_category_id: "", description: "", amount: "" }])
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const invoice = await createInvoice.mutateAsync({
        student: Number(studentId),
        term: Number(termId),
        items: items
          .filter((i) => i.fee_category_id && i.amount)
          .map((i) => ({ fee_category_id: Number(i.fee_category_id), description: i.description, amount: i.amount })),
      })
      navigate(`/fees/${invoice.id}`)
    } catch {
      setError("Could not create the invoice. Check that all fields are filled in correctly.")
    }
  }

  return (
    <AppShell title="New invoice">
      <form onSubmit={handleSubmit} className="max-w-xl space-y-6">
        <div>
          <label htmlFor="student" className="block text-sm font-medium text-text-primary">
            Student
          </label>
          <select
            id="student"
            required
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          >
            <option value="" disabled>
              {studentsQuery.isPending ? "Loading…" : "Select a student"}
            </option>
            {studentsQuery.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.admission_number} — {s.full_name}
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
          <div className="flex items-center justify-between">
            <span className="block text-sm font-medium text-text-primary">Line items</span>
            <button type="button" onClick={addItem} className="text-xs font-medium text-ledger hover:underline">
              + Add item
            </button>
          </div>
          <div className="mt-2 space-y-2">
            {items.map((item, i) => (
              <div key={i} className="flex gap-2">
                <select
                  required
                  value={item.fee_category_id}
                  onChange={(e) => updateItem(i, "fee_category_id", e.target.value)}
                  className="w-40 rounded border border-line bg-surface px-2 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                >
                  <option value="" disabled>
                    Category
                  </option>
                  {feeCategoriesQuery.data?.map((fc) => (
                    <option key={fc.id} value={fc.id}>
                      {fc.name}
                    </option>
                  ))}
                </select>
                <input
                  value={item.description}
                  onChange={(e) => updateItem(i, "description", e.target.value)}
                  placeholder="Description (optional)"
                  className="flex-1 rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                />
                <input
                  required
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={item.amount}
                  onChange={(e) => updateItem(i, "amount", e.target.value)}
                  placeholder="Amount"
                  className="w-32 rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                />
                {items.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeItem(i)}
                    className="px-2 text-sm text-text-muted hover:text-red"
                    aria-label="Remove item"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
          <p className="mt-3 text-sm text-text-muted">
            Total: <span className="font-display text-base text-text-primary">KSh {total.toLocaleString()}</span>
          </p>
        </div>

        {error && <p className="border-l-2 border-red pl-3 text-sm text-red">{error}</p>}

        <button
          type="submit"
          disabled={createInvoice.isPending}
          className="rounded bg-ink px-4 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
        >
          {createInvoice.isPending ? "Creating…" : "Create invoice"}
        </button>
      </form>
    </AppShell>
  )
}
