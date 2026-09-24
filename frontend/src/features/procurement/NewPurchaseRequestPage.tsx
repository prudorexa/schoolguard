import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useCreatePurchaseRequest, useDepartments } from "./useProcurement"

interface LineItem {
  description: string
  quantity: string
  unit_price: string
}

export function NewPurchaseRequestPage() {
  const navigate = useNavigate()
  const departmentsQuery = useDepartments()
  const createPR = useCreatePurchaseRequest()

  const [title, setTitle] = useState("")
  const [departmentId, setDepartmentId] = useState("")
  const [items, setItems] = useState<LineItem[]>([{ description: "", quantity: "1", unit_price: "" }])
  const [error, setError] = useState<string | null>(null)

  function updateItem(index: number, field: keyof LineItem, value: string) {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)))
  }

  function addItem() {
    setItems((prev) => [...prev, { description: "", quantity: "1", unit_price: "" }])
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const total = items.reduce((sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0), 0)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const pr = await createPR.mutateAsync({
        title,
        department: Number(departmentId),
        items: items
          .filter((i) => i.description && i.unit_price)
          .map((i) => ({ description: i.description, quantity: Number(i.quantity), unit_price: i.unit_price })),
      })
      navigate(`/procurement/${pr.id}`)
    } catch {
      setError("Could not create the request. Check that all fields are filled in correctly.")
    }
  }

  return (
    <AppShell title="New purchase request">
      <form onSubmit={handleSubmit} className="max-w-xl space-y-6">
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-text-primary">
            What is this for?
          </label>
          <input
            id="title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Laboratory equipment"
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          />
        </div>

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
          <div className="flex items-center justify-between">
            <span className="block text-sm font-medium text-text-primary">Line items</span>
            <button type="button" onClick={addItem} className="text-xs font-medium text-ledger hover:underline">
              + Add item
            </button>
          </div>
          <div className="mt-2 space-y-2">
            {items.map((item, i) => (
              <div key={i} className="flex gap-2">
                <input
                  required
                  value={item.description}
                  onChange={(e) => updateItem(i, "description", e.target.value)}
                  placeholder="Description"
                  className="flex-1 rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                />
                <input
                  required
                  type="number"
                  min="1"
                  value={item.quantity}
                  onChange={(e) => updateItem(i, "quantity", e.target.value)}
                  placeholder="Qty"
                  className="w-20 rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
                />
                <input
                  required
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={item.unit_price}
                  onChange={(e) => updateItem(i, "unit_price", e.target.value)}
                  placeholder="Unit price"
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
            Estimated total: <span className="font-display text-base text-text-primary">KSh {total.toLocaleString()}</span>
          </p>
        </div>

        {error && <p className="border-l-2 border-red pl-3 text-sm text-red">{error}</p>}

        <button
          type="submit"
          disabled={createPR.isPending}
          className="rounded bg-ink px-4 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
        >
          {createPR.isPending ? "Saving…" : "Save as draft"}
        </button>
      </form>
    </AppShell>
  )
}
