import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useCreateSupplier } from "./useSuppliers"

function apiErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  if (anyErr?.response?.status === 403) return "You do not have permission to do this."
  const data = anyErr?.response?.data
  // Duplicate supplier names come back as a bare array (from
  // TenantScopedViewSetMixin's IntegrityError handling); other field
  // errors come back as {field: [messages]} the normal DRF way. Handle
  // both rather than assuming one.
  if (Array.isArray(data) && typeof data[0] === "string") return data[0]
  if (data && typeof data === "object") {
    const obj = data as { name?: string[] }
    if (obj.name?.length) return obj.name[0]
  }
  return "Could not create the supplier. Check that all fields are filled in correctly."
}

export function NewSupplierPage() {
  const navigate = useNavigate()
  const createSupplier = useCreateSupplier()

  const [name, setName] = useState("")
  const [contactPerson, setContactPerson] = useState("")
  const [phone, setPhone] = useState("")
  const [email, setEmail] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createSupplier.mutateAsync({
        name,
        contact_person: contactPerson,
        phone,
        email,
      })
      navigate("/suppliers")
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <AppShell title="New supplier">
      <form onSubmit={handleSubmit} className="max-w-md space-y-5">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-text-primary">
            Supplier name
          </label>
          <input
            id="name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          />
        </div>

        <div>
          <label htmlFor="contact" className="block text-sm font-medium text-text-primary">
            Contact person <span className="font-normal text-text-muted">(optional)</span>
          </label>
          <input
            id="contact"
            value={contactPerson}
            onChange={(e) => setContactPerson(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-text-primary">
              Phone <span className="font-normal text-text-muted">(optional)</span>
            </label>
            <input
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-text-primary">
              Email <span className="font-normal text-text-muted">(optional)</span>
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
          </div>
        </div>

        {error && <p className="border-l-2 border-red pl-3 text-sm text-red">{error}</p>}

        <button
          type="submit"
          disabled={createSupplier.isPending}
          className="rounded bg-ink px-4 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
        >
          {createSupplier.isPending ? "Saving…" : "Add supplier"}
        </button>
      </form>
    </AppShell>
  )
}
